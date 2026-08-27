from __future__ import annotations

from statistics import median
from typing import Sequence

from .engine import Signal
from .moex import Candle


def _sma(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def _true_ranges(candles: Sequence[Candle]) -> list[float]:
    if len(candles) < 2:
        return []
    out: list[float] = []
    prev_close = candles[0].close
    for c in candles[1:]:
        tr = max(c.high - c.low, abs(c.high - prev_close), abs(c.low - prev_close))
        out.append(tr)
        prev_close = c.close
    return out


def market_structure_signal(candles: Sequence[Candle]) -> Signal | None:
    if len(candles) < 50:
        return None
    closes = [c.close for c in candles]
    close = closes[-1]
    ma20 = _sma(closes, 20)
    ma50 = _sma(closes, 50)
    if ma20 is None or ma50 is None:
        return None

    score = 0.0
    if close < ma20:
        score += 25
    if close < ma50:
        score += 25
    if ma20 < ma50:
        score += 20
    if close <= min(closes[-20:]):
        score += 20
    if closes[-1] < closes[-6]:
        score += 10
    return Signal(min(score, 100.0))


def levels_momentum_signal(candles: Sequence[Candle]) -> Signal | None:
    if len(candles) < 21:
        return None
    closes = [c.close for c in candles]
    close = closes[-1]
    ret5 = close / closes[-6] - 1.0
    ret20 = close / closes[-21] - 1.0
    low20 = min(closes[-20:])

    score = 0.0
    if ret5 <= -0.03:
        score += 30
    elif ret5 < 0:
        score += 15
    if ret20 <= -0.08:
        score += 35
    elif ret20 <= -0.03:
        score += 20
    if close <= low20 * 1.01:
        score += 25
    if close < closes[-2]:
        score += 10
    return Signal(min(score, 100.0))


def volatility_liquidity_signal(candles: Sequence[Candle]) -> Signal | None:
    if len(candles) < 40:
        return None
    trs = _true_ranges(candles)
    if len(trs) < 30:
        return None
    recent = sum(trs[-14:]) / 14
    baseline = median(trs[-40:-14]) if len(trs[-40:-14]) else None
    if not baseline or baseline <= 0:
        return None
    ratio = recent / baseline

    score = 0.0
    if ratio >= 2.0:
        score += 70
    elif ratio >= 1.5:
        score += 50
    elif ratio >= 1.2:
        score += 30
    else:
        score += 10

    gap_downs = 0
    for prev, cur in zip(candles[-11:-1], candles[-10:]):
        if cur.open < prev.low:
            gap_downs += 1
    score += min(gap_downs * 7.5, 30)
    return Signal(min(score, 100.0))


def derive_index_signals(candles: Sequence[Candle]) -> dict[str, Signal]:
    result: dict[str, Signal] = {}
    for key, fn in (
        ("market_structure", market_structure_signal),
        ("levels_momentum", levels_momentum_signal),
        ("volatility_liquidity", volatility_liquidity_signal),
    ):
        signal = fn(candles)
        if signal is not None:
            result[key] = signal
    return result
