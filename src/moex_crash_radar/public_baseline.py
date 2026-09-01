from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from statistics import median
from typing import Sequence

from .moex import Candle


@dataclass(frozen=True)
class BaselineConfig:
    swing_lookback: int = 3
    atr_period: int = 14
    rvol_sessions: int = 10
    rvol_threshold: float = 1.0
    location_atr_tolerance: float = 0.35
    stop_atr_buffer: float = 0.20
    max_stop_atr: float = 1.50
    min_rr: float = 2.0
    time_stop_bars: int = 4
    fee_bps_round_trip: float = 2.0
    slippage_bps_round_trip: float = 2.0
    max_cost_r: float = 0.25


@dataclass(frozen=True)
class FeatureRow:
    index: int
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    atr: float | None
    regime: str
    location_long: bool
    location_short: bool
    rvol: float | None
    long_trigger: bool
    short_trigger: bool


@dataclass(frozen=True)
class Trade:
    model: str
    direction: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    exit: float
    gross_r: float
    cost_r: float
    net_r: float
    exit_reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BacktestSummary:
    model: str
    trades: int
    wins: int
    losses: int
    win_rate_pct: float | None
    expectancy_r: float | None
    profit_factor: float | None
    max_drawdown_r: float | None
    total_net_r: float

    def to_dict(self) -> dict:
        return asdict(self)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _rolling_atr(candles: Sequence[Candle], period: int) -> list[float | None]:
    trs: list[float] = []
    out: list[float | None] = []
    previous_close: float | None = None
    for candle in candles:
        tr = candle.high - candle.low if previous_close is None else max(
            candle.high - candle.low,
            abs(candle.high - previous_close),
            abs(candle.low - previous_close),
        )
        trs.append(tr)
        previous_close = candle.close
        out.append(sum(trs[-period:]) / period if len(trs) >= period else None)
    return out


def _same_hour_rvol(candles: Sequence[Candle], lookback_sessions: int) -> list[float | None]:
    by_hour: dict[int, list[float]] = {}
    out: list[float | None] = []
    for candle in candles:
        hour = _dt(candle.begin).hour
        history = by_hour.setdefault(hour, [])
        if candle.volume is None or len(history) < lookback_sessions:
            out.append(None)
        else:
            base = median(history[-lookback_sessions:])
            out.append((float(candle.volume) / base) if base > 0 else None)
        if candle.volume is not None:
            history.append(float(candle.volume))
    return out


def _bucket4h(value: str) -> tuple[str, int]:
    dt = _dt(value)
    return dt.date().isoformat(), (dt.hour // 4) * 4


def _four_hour_regimes(candles: Sequence[Candle]) -> list[str]:
    """Map each 1H bar to regime from fully closed preceding 4H clock buckets.

    Current in-progress 4H bucket is never used, preventing higher-timeframe
    look-ahead. Two completed buckets define HH+HL / LH+LL; otherwise RANGE.
    """
    out: list[str] = []
    completed: list[tuple[float, float]] = []
    active_key: tuple[str, int] | None = None
    active_high: float | None = None
    active_low: float | None = None

    for candle in candles:
        key = _bucket4h(candle.begin)
        if active_key is None:
            active_key, active_high, active_low = key, candle.high, candle.low
        elif key != active_key:
            assert active_high is not None and active_low is not None
            completed.append((active_high, active_low))
            active_key, active_high, active_low = key, candle.high, candle.low
        else:
            active_high = max(float(active_high), candle.high)
            active_low = min(float(active_low), candle.low)

        if len(completed) < 2:
            out.append("RANGE")
        else:
            old_high, old_low = completed[-2]
            new_high, new_low = completed[-1]
            if new_high > old_high and new_low > old_low:
                out.append("BULL")
            elif new_high < old_high and new_low < old_low:
                out.append("BEAR")
            else:
                out.append("RANGE")
    return out


def _previous_day_levels(candles: Sequence[Candle]) -> list[tuple[float | None, float | None]]:
    out: list[tuple[float | None, float | None]] = []
    current_day: str | None = None
    day_high: float | None = None
    day_low: float | None = None
    previous: tuple[float | None, float | None] = (None, None)
    for candle in candles:
        day = candle.begin[:10]
        if current_day is None:
            current_day = day
        elif day != current_day:
            previous = (day_high, day_low)
            current_day, day_high, day_low = day, None, None
        out.append(previous)
        day_high = candle.high if day_high is None else max(day_high, candle.high)
        day_low = candle.low if day_low is None else min(day_low, candle.low)
    return out


def _location(
    candles: Sequence[Candle],
    i: int,
    atr: float | None,
    lookback: int,
    tolerance_atr: float,
    pdh: float | None,
    pdl: float | None,
) -> tuple[bool, bool]:
    if atr is None or i < lookback:
        return False, False
    prev = candles[i - lookback : i]
    local_support = min(c.low for c in prev)
    local_resistance = max(c.high for c in prev)
    tolerance = tolerance_atr * atr
    close = candles[i].close

    supports = [local_support] + ([pdl] if pdl is not None else [])
    resistances = [local_resistance] + ([pdh] if pdh is not None else [])
    long_ok = any(close <= level + tolerance for level in supports) or close > min(resistances)
    short_ok = any(close >= level - tolerance for level in resistances) or close < max(supports)
    return long_ok, short_ok


def build_features(candles: Sequence[Candle], config: BaselineConfig = BaselineConfig()) -> list[FeatureRow]:
    candles = sorted(candles, key=lambda c: _dt(c.begin))
    atrs = _rolling_atr(candles, config.atr_period)
    rvols = _same_hour_rvol(candles, config.rvol_sessions)
    regimes = _four_hour_regimes(candles)
    previous_day = _previous_day_levels(candles)
    rows: list[FeatureRow] = []

    for i, candle in enumerate(candles):
        atr = atrs[i]
        pdh, pdl = previous_day[i]
        long_loc, short_loc = _location(
            candles, i, atr, config.swing_lookback,
            config.location_atr_tolerance, pdh, pdl,
        )
        long_trigger = i >= 2 and candles[i - 1].low > candles[i - 2].low and candle.close > candles[i - 1].high
        short_trigger = i >= 2 and candles[i - 1].high < candles[i - 2].high and candle.close < candles[i - 1].low
        rows.append(FeatureRow(
            index=i,
            timestamp=candle.begin,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=float(candle.volume or 0.0),
            atr=atr,
            regime=regimes[i],
            location_long=long_loc,
            location_short=short_loc,
            rvol=rvols[i],
            long_trigger=long_trigger,
            short_trigger=short_trigger,
        ))
    return rows


def _cost_r(entry: float, risk_distance: float, config: BaselineConfig) -> float:
    total_bps = config.fee_bps_round_trip + config.slippage_bps_round_trip
    return (entry * total_bps / 10000.0) / risk_distance if risk_distance > 0 else 0.0


def _simulate_trade(
    candles: Sequence[Candle], rows: Sequence[FeatureRow], i: int,
    *, model: str, direction: str, config: BaselineConfig,
) -> Trade | None:
    if i + 1 >= len(candles):
        return None
    signal, entry_bar = rows[i], candles[i + 1]
    entry, atr = entry_bar.open, signal.atr
    if atr is None or atr <= 0:
        return None

    lookback = candles[max(0, i - config.swing_lookback + 1) : i + 1]
    if direction == "LONG":
        stop = min(c.low for c in lookback) - config.stop_atr_buffer * atr
        risk = entry - stop
    else:
        stop = max(c.high for c in lookback) + config.stop_atr_buffer * atr
        risk = stop - entry
    if risk <= 0 or risk > config.max_stop_atr * atr:
        return None

    cost_r = _cost_r(entry, risk, config)
    if cost_r > config.max_cost_r:
        # A nominally valid stop can be so tight that even conservative proxy
        # costs dominate the entire trade. Such observations are not comparable
        # in R-space and must fail closed instead of corrupting expectancy/PF.
        return None

    obstacle_window = candles[max(0, i - 24) : i + 1]
    if direction == "LONG":
        obstacles = [c.high for c in obstacle_window if c.high > entry]
        if obstacles and (min(obstacles) - entry) / risk < config.min_rr:
            return None
        target = entry + 2.0 * risk
    else:
        obstacles = [c.low for c in obstacle_window if c.low < entry]
        if obstacles and (entry - max(obstacles)) / risk < config.min_rr:
            return None
        target = entry - 2.0 * risk

    last_index = min(len(candles) - 1, i + max(config.time_stop_bars, 1))
    exit_price, reason = candles[last_index].close, "TIME"
    for j in range(i + 1, last_index + 1):
        bar = candles[j]
        stop_hit = bar.low <= stop if direction == "LONG" else bar.high >= stop
        target_hit = bar.high >= target if direction == "LONG" else bar.low <= target
        if stop_hit:  # conservative when target and stop are both inside one OHLC bar
            exit_price, reason, last_index = stop, "STOP", j
            break
        if target_hit:
            exit_price, reason, last_index = target, "TARGET_2R", j
            break

    gross_r = (exit_price - entry) / risk if direction == "LONG" else (entry - exit_price) / risk
    return Trade(
        model=model,
        direction=direction,
        signal_time=signal.timestamp,
        entry_time=entry_bar.begin,
        exit_time=candles[last_index].begin,
        entry=entry,
        stop=stop,
        exit=exit_price,
        gross_r=round(gross_r, 4),
        cost_r=round(cost_r, 4),
        net_r=round(gross_r - cost_r, 4),
        exit_reason=reason,
    )


def run_model(candles: Sequence[Candle], model: str, config: BaselineConfig = BaselineConfig()) -> list[Trade]:
    if model not in {"M0", "M1", "M5"}:
        raise ValueError("public baseline supports only M0, M1, M5")
    candles = sorted(candles, key=lambda c: _dt(c.begin))
    rows = build_features(candles, config)
    trades: list[Trade] = []
    next_free_index = 0

    for i, row in enumerate(rows):
        if i < next_free_index or row.atr is None:
            continue
        if row.regime == "BULL" and row.long_trigger:
            direction = "LONG"
        elif row.regime == "BEAR" and row.short_trigger:
            direction = "SHORT"
        else:
            continue

        if model in {"M1", "M5"}:
            if direction == "LONG" and not row.location_long:
                continue
            if direction == "SHORT" and not row.location_short:
                continue
        if model == "M5" and (row.rvol is None or row.rvol < config.rvol_threshold):
            continue

        trade = _simulate_trade(candles, rows, i, model=model, direction=direction, config=config)
        if trade is not None:
            trades.append(trade)
            exit_index = next((k for k, c in enumerate(candles) if c.begin == trade.exit_time), i + 1)
            next_free_index = exit_index + 1
    return trades


def summarize(model: str, trades: Sequence[Trade]) -> BacktestSummary:
    if not trades:
        return BacktestSummary(model, 0, 0, 0, None, None, None, None, 0.0)
    values = [t.net_r for t in trades]
    wins = [v for v in values if v > 0]
    losses = [v for v in values if v <= 0]
    gross_profit, gross_loss = sum(wins), abs(sum(losses))
    equity = peak = max_dd = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return BacktestSummary(
        model=model,
        trades=len(values),
        wins=len(wins),
        losses=len(losses),
        win_rate_pct=round(100.0 * len(wins) / len(values), 2),
        expectancy_r=round(sum(values) / len(values), 4),
        profit_factor=round(gross_profit / gross_loss, 4) if gross_loss > 0 else None,
        max_drawdown_r=round(max_dd, 4),
        total_net_r=round(sum(values), 4),
    )


def run_ablation(candles: Sequence[Candle], config: BaselineConfig = BaselineConfig()) -> dict[str, BacktestSummary]:
    return {model: summarize(model, run_model(candles, model, config)) for model in ("M0", "M1", "M5")}
