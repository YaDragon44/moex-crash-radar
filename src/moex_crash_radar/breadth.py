from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Mapping, Sequence

from .engine import Signal
from .moex import Candle


@dataclass(frozen=True)
class BreadthSnapshot:
    universe_size: int
    usable_size: int
    pct_above_ma20: float
    pct_above_ma50: float
    pct_new_20d_lows: float
    pct_new_20d_highs: float
    advance_decline_ratio: float
    breadth_return_5d: float


def _sma(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def calculate_breadth(universe: Mapping[str, Sequence[Candle]]) -> BreadthSnapshot | None:
    metrics = []
    five_day_returns: list[float] = []
    adv = 0
    dec = 0

    for candles in universe.values():
        if len(candles) < 51:
            continue
        closes = [c.close for c in candles]
        close = closes[-1]
        ma20 = _sma(closes, 20)
        ma50 = _sma(closes, 50)
        if ma20 is None or ma50 is None:
            continue

        metrics.append(
            (
                close > ma20,
                close > ma50,
                close <= min(closes[-20:]),
                close >= max(closes[-20:]),
            )
        )
        five_day_returns.append((close / closes[-6] - 1.0) * 100.0)
        if close > closes[-2]:
            adv += 1
        elif close < closes[-2]:
            dec += 1

    usable = len(metrics)
    if usable == 0:
        return None

    pct = lambda count: round(100.0 * count / usable, 2)
    above20 = pct(sum(1 for x in metrics if x[0]))
    above50 = pct(sum(1 for x in metrics if x[1]))
    new_lows = pct(sum(1 for x in metrics if x[2]))
    new_highs = pct(sum(1 for x in metrics if x[3]))
    ad_ratio = round(adv / max(dec, 1), 3)

    return BreadthSnapshot(
        universe_size=len(universe),
        usable_size=usable,
        pct_above_ma20=above20,
        pct_above_ma50=above50,
        pct_new_20d_lows=new_lows,
        pct_new_20d_highs=new_highs,
        advance_decline_ratio=ad_ratio,
        breadth_return_5d=round(mean(five_day_returns), 2),
    )


def breadth_signal(snapshot: BreadthSnapshot) -> Signal:
    score = 0.0
    if snapshot.pct_above_ma20 < 30:
        score += 25
    elif snapshot.pct_above_ma20 < 45:
        score += 15

    if snapshot.pct_above_ma50 < 30:
        score += 30
    elif snapshot.pct_above_ma50 < 45:
        score += 18

    if snapshot.pct_new_20d_lows >= 35:
        score += 25
    elif snapshot.pct_new_20d_lows >= 20:
        score += 15

    if snapshot.advance_decline_ratio < 0.5:
        score += 15
    elif snapshot.advance_decline_ratio < 0.8:
        score += 8

    if snapshot.breadth_return_5d <= -5:
        score += 5

    return Signal(min(score, 100.0))


def index_vs_breadth_divergence(index_candles: Sequence[Candle], snapshot: BreadthSnapshot) -> bool:
    if len(index_candles) < 6:
        return False
    idx_ret = (index_candles[-1].close / index_candles[-6].close - 1.0) * 100.0
    return idx_ret >= -1.0 and snapshot.breadth_return_5d <= -5.0
