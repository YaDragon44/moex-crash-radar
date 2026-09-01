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
    risk_accepted_m0: int
    risk_accepted_m1: int
    risk_accepted_m5: int

    def to_dict(self) -> dict:
        return asdict(self)


def diagnose_filters(candles: Sequence[Candle], config: BaselineConfig = BaselineConfig()) -> FilterFunnel:
    candles = sorted(candles, key=lambda c: _dt(c.begin))
    rows = build_features(candles, config)
    candidates = location_pass = rvol_pass = 0
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
        risk_accepted_m0=accepted_m0,
        risk_accepted_m1=accepted_m1,
        risk_accepted_m5=accepted_m5,
    )
