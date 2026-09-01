from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from .moex import Candle
from .public_baseline import BaselineConfig, _dt, _simulate_trade, build_features


@dataclass(frozen=True)
class FilterFunnel:
    regime_trigger_candidates: int
    location_pass: int
    rvol_pass: int
    stop_invalid_or_too_wide: int
    insufficient_rr: int
    risk_accepted_m0: int
    risk_accepted_m1: int
    risk_accepted_m5: int

    def to_dict(self) -> dict:
        return asdict(self)


def _risk_rejection_reason(
    candles: Sequence[Candle], i: int, *, direction: str, config: BaselineConfig, atr: float
) -> str:
    if i + 1 >= len(candles):
        return "NO_NEXT_BAR"
    entry = candles[i + 1].open
    lookback = candles[max(0, i - config.swing_lookback + 1) : i + 1]
    if direction == "LONG":
        stop = min(c.low for c in lookback) - config.stop_atr_buffer * atr
        risk = entry - stop
    else:
        stop = max(c.high for c in lookback) + config.stop_atr_buffer * atr
        risk = stop - entry
    if risk <= 0 or risk > config.max_stop_atr * atr:
        return "STOP_INVALID_OR_TOO_WIDE"

    obstacle_window = candles[max(0, i - 24) : i + 1]
    if direction == "LONG":
        obstacles = [c.high for c in obstacle_window if c.high > entry]
        if obstacles and (min(obstacles) - entry) / risk < config.min_rr:
            return "INSUFFICIENT_RR"
    else:
        obstacles = [c.low for c in obstacle_window if c.low < entry]
        if obstacles and (entry - max(obstacles)) / risk < config.min_rr:
            return "INSUFFICIENT_RR"
    return "ACCEPTED"


def diagnose_filters(candles: Sequence[Candle], config: BaselineConfig = BaselineConfig()) -> FilterFunnel:
    candles = sorted(candles, key=lambda c: _dt(c.begin))
    rows = build_features(candles, config)
    candidates = location_pass = rvol_pass = 0
    stop_reject = rr_reject = 0
    accepted_m0 = accepted_m1 = accepted_m5 = 0

    for i, row in enumerate(rows):
        if row.atr is None:
            continue
        if row.regime == "BULL" and row.long_trigger:
            direction = "LONG"
        elif row.regime == "BEAR" and row.short_trigger:
            direction = "SHORT"
        else:
            continue
        candidates += 1

        reason = _risk_rejection_reason(candles, i, direction=direction, config=config, atr=row.atr)
        if reason == "STOP_INVALID_OR_TOO_WIDE":
            stop_reject += 1
        elif reason == "INSUFFICIENT_RR":
            rr_reject += 1

        if _simulate_trade(candles, rows, i, model="M0", direction=direction, config=config) is not None:
            accepted_m0 += 1

        loc_ok = row.location_long if direction == "LONG" else row.location_short
        if not loc_ok:
            continue
        location_pass += 1
        if _simulate_trade(candles, rows, i, model="M1", direction=direction, config=config) is not None:
            accepted_m1 += 1

        if row.rvol is None or row.rvol < config.rvol_threshold:
            continue
        rvol_pass += 1
        if _simulate_trade(candles, rows, i, model="M5", direction=direction, config=config) is not None:
            accepted_m5 += 1

    return FilterFunnel(
        regime_trigger_candidates=candidates,
        location_pass=location_pass,
        rvol_pass=rvol_pass,
        stop_invalid_or_too_wide=stop_reject,
        insufficient_rr=rr_reject,
        risk_accepted_m0=accepted_m0,
        risk_accepted_m1=accepted_m1,
        risk_accepted_m5=accepted_m5,
    )
