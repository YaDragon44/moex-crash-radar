from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable, Sequence

from .contract_costs import ContractSpec, apply_contract_cost
from .public_baseline import BaselineConfig, Trade, build_features, summarize
from .roll_chain import RollBar

GEOMETRIES = ("CONTROL", "ATR_INVALIDATION", "HTF_LIQUIDITY", "TIME_INVALIDATION")


@dataclass(frozen=True)
class GeometryResult:
    model: str
    geometry: str
    candidates: int
    accepted: int
    preservation_pct: float
    expectancy_r: float | None
    profit_factor: float | None
    max_drawdown_r: float | None
    total_net_r: float
    cost_coverage_pct: float

    def to_dict(self) -> dict:
        return asdict(self)


def _segments(bars: Sequence[RollBar]) -> list[tuple[str, list]]:
    out: list[tuple[str, list]] = []
    active = None
    candles: list = []
    for row in bars:
        if active is None:
            active = row.secid
        if row.secid != active:
            out.append((active, candles))
            active, candles = row.secid, []
        candles.append(row.candle)
    if active is not None and candles:
        out.append((active, candles))
    return out


def _candidate_indices(candles, model: str, config: BaselineConfig):
    rows = build_features(candles, config)
    out = []
    for i, row in enumerate(rows):
        if row.atr is None:
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
        out.append((i, direction, rows))
    return out


def _structural_stop(candles, i: int, direction: str, atr: float, config: BaselineConfig) -> float:
    lookback = candles[max(0, i - config.swing_lookback + 1): i + 1]
    if direction == "LONG":
        return min(c.low for c in lookback) - config.stop_atr_buffer * atr
    return max(c.high for c in lookback) + config.stop_atr_buffer * atr


def _htf_obstacle(candles, i: int, entry: float, direction: str) -> float | None:
    # Use completed 4H blocks only; intentionally coarser than every 1H extreme.
    blocks = []
    active_key = None
    high = low = None
    for c in candles[max(0, i - 48): i + 1]:
        dt = __import__("datetime").datetime.fromisoformat(c.begin)
        key = (dt.date().isoformat(), (dt.hour // 4) * 4)
        if active_key is None:
            active_key, high, low = key, c.high, c.low
        elif key != active_key:
            blocks.append((high, low))
            active_key, high, low = key, c.high, c.low
        else:
            high, low = max(high, c.high), min(low, c.low)
    if direction == "LONG":
        values = [h for h, _ in blocks if h > entry]
        return min(values) if values else None
    values = [l for _, l in blocks if l < entry]
    return max(values) if values else None


def _simulate(candles, i: int, direction: str, rows, geometry: str, config: BaselineConfig) -> Trade | None:
    if i + 1 >= len(candles):
        return None
    signal = rows[i]
    atr = signal.atr
    if atr is None or atr <= 0:
        return None
    entry_bar = candles[i + 1]
    entry = entry_bar.open
    structural = _structural_stop(candles, i, direction, atr, config)

    if geometry == "ATR_INVALIDATION":
        stop = entry - 1.25 * atr if direction == "LONG" else entry + 1.25 * atr
        # Structure remains a confirmation: do not place an ATR stop beyond a wildly distant invalidation level.
        structural_distance = (entry - structural) if direction == "LONG" else (structural - entry)
        if structural_distance <= 0 or structural_distance > 2.5 * atr:
            return None
    else:
        stop = structural

    risk = (entry - stop) if direction == "LONG" else (stop - entry)
    if risk <= 0 or risk > config.max_stop_atr * atr:
        return None

    if geometry == "CONTROL":
        window = candles[max(0, i - 24): i + 1]
        if direction == "LONG":
            obstacles = [c.high for c in window if c.high > entry]
            if obstacles and (min(obstacles) - entry) / risk < config.min_rr:
                return None
        else:
            obstacles = [c.low for c in window if c.low < entry]
            if obstacles and (entry - max(obstacles)) / risk < config.min_rr:
                return None
    elif geometry == "HTF_LIQUIDITY":
        obstacle = _htf_obstacle(candles, i, entry, direction)
        if obstacle is not None:
            rr = ((obstacle - entry) / risk) if direction == "LONG" else ((entry - obstacle) / risk)
            if rr < config.min_rr:
                return None
    elif geometry not in {"ATR_INVALIDATION", "TIME_INVALIDATION"}:
        raise ValueError(f"unknown geometry {geometry}")

    target = entry + 2.0 * risk if direction == "LONG" else entry - 2.0 * risk
    last_index = min(len(candles) - 1, i + max(config.time_stop_bars, 1))
    exit_price, reason = candles[last_index].close, "TIME"
    for j in range(i + 1, last_index + 1):
        bar = candles[j]
        stop_hit = bar.low <= stop if direction == "LONG" else bar.high >= stop
        target_hit = bar.high >= target if direction == "LONG" else bar.low <= target
        if stop_hit:
            exit_price, reason, last_index = stop, "STOP", j
            break
        if target_hit:
            exit_price, reason, last_index = target, "TARGET_2R", j
            break
    gross_r = (exit_price - entry) / risk if direction == "LONG" else (entry - exit_price) / risk
    return Trade(
        model="", direction=direction, signal_time=signal.timestamp,
        entry_time=entry_bar.begin, exit_time=candles[last_index].begin,
        entry=entry, stop=stop, exit=exit_price,
        gross_r=round(gross_r, 4), cost_r=0.0, net_r=round(gross_r, 4), exit_reason=reason,
    )


def run_geometry(
    bars: Sequence[RollBar], model: str, geometry: str,
    config: BaselineConfig = BaselineConfig(), *, specs: dict[str, ContractSpec] | None = None,
) -> GeometryResult:
    if model not in {"M0", "M1", "M5"}:
        raise ValueError("models: M0/M1/M5")
    if geometry not in GEOMETRIES:
        raise ValueError(f"geometries: {GEOMETRIES}")
    specs = specs or {}
    trades: list[Trade] = []
    candidates = priced = 0
    for secid, candles in _segments(bars):
        gross_config = replace(config, fee_bps_round_trip=0.0, slippage_bps_round_trip=0.0)
        next_free = 0
        for i, direction, rows in _candidate_indices(candles, model, gross_config):
            candidates += 1
            if i < next_free:
                continue
            trade = _simulate(candles, i, direction, rows, geometry, gross_config)
            if trade is None:
                continue
            trade = replace(trade, model=f"{model}:{geometry}")
            spec = specs.get(secid)
            if spec is not None:
                trade = apply_contract_cost(trade, spec)
                priced += 1
            trades.append(trade)
            exit_index = next((k for k, c in enumerate(candles) if c.begin == trade.exit_time), i + 1)
            next_free = exit_index + 1
    summary = summarize(f"{model}:{geometry}", trades)
    coverage = 100.0 * priced / len(trades) if trades else 100.0
    return GeometryResult(
        model=model, geometry=geometry, candidates=candidates, accepted=summary.trades,
        preservation_pct=round(100.0 * summary.trades / candidates, 2) if candidates else 0.0,
        expectancy_r=summary.expectancy_r, profit_factor=summary.profit_factor,
        max_drawdown_r=summary.max_drawdown_r, total_net_r=summary.total_net_r,
        cost_coverage_pct=round(coverage, 2),
    )


def compare_geometries(
    bars: Sequence[RollBar], *, models: Iterable[str] = ("M0", "M1", "M5"),
    geometries: Iterable[str] = GEOMETRIES, config: BaselineConfig = BaselineConfig(),
    specs: dict[str, ContractSpec] | None = None,
) -> list[GeometryResult]:
    return [run_geometry(bars, m, g, config, specs=specs) for m in models for g in geometries]
