from __future__ import annotations

from statistics import median
from typing import Mapping, Sequence

from .crowd import CrowdInputs
from .moex import Candle


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _sma(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def momentum_sentiment(candles: Sequence[Candle]) -> float | None:
    """Map trailing 5d/20d returns to a 0..100 crowd direction score.

    50 is balanced, high values indicate persistent positive price behaviour,
    low values indicate persistent negative price behaviour. This is a research
    feature, not a return forecast.
    """
    if len(candles) < 21:
        return None
    closes = [c.close for c in candles]
    ret5 = closes[-1] / closes[-6] - 1.0
    ret20 = closes[-1] / closes[-21] - 1.0
    score = 50.0 + ret5 * 250.0 + ret20 * 125.0
    return round(_clamp(score), 2)


def volatility_sentiment(candles: Sequence[Candle]) -> float | None:
    """Translate realised range expansion into crowd calm/fear on 0..100.

    Higher score means calmer volatility conditions; lower score means range
    expansion usually associated with fear/panic. Only trailing observations are
    used.
    """
    if len(candles) < 41:
        return None
    trs: list[float] = []
    prev = candles[0].close
    for candle in candles[1:]:
        trs.append(max(candle.high - candle.low, abs(candle.high - prev), abs(candle.low - prev)))
        prev = candle.close
    recent = sum(trs[-14:]) / 14
    baseline_window = trs[-40:-14]
    baseline = median(baseline_window) if baseline_window else None
    if baseline is None or baseline <= 0:
        return None
    ratio = recent / baseline
    # ratio <= 0.8 => very calm; ratio >= 2.0 => severe expansion.
    score = 90.0 - ((ratio - 0.8) / 1.2) * 80.0
    return round(_clamp(score), 2)


def breadth_sentiment(equity_histories: Mapping[str, Sequence[Candle]]) -> float | None:
    """Measure how broadly positive the current equity tape is.

    Combines share of constituents above 20d SMA and share with positive 5d
    return. Requires at least 5 usable securities to avoid false precision.
    """
    above = positive = usable = 0
    for candles in equity_histories.values():
        if len(candles) < 21:
            continue
        closes = [c.close for c in candles]
        ma20 = _sma(closes, 20)
        if ma20 is None:
            continue
        usable += 1
        above += int(closes[-1] > ma20)
        positive += int(closes[-1] > closes[-6])
    if usable < 5:
        return None
    score = 50.0 * (above / usable) + 50.0 * (positive / usable)
    return round(_clamp(score), 2)


def volume_sentiment(equity_histories: Mapping[str, Sequence[Candle]]) -> float | None:
    """Estimate directional participation from trailing five sessions' turnover.

    Up-session value is compared with up+down-session value. Flat sessions are
    ignored. At least 5 securities with usable turnover are required.
    """
    up_value = down_value = 0.0
    usable = 0
    for candles in equity_histories.values():
        if len(candles) < 6:
            continue
        local_used = False
        for prev, cur in zip(candles[-6:-1], candles[-5:]):
            turnover = cur.value
            if turnover is None or turnover <= 0:
                continue
            if cur.close > prev.close:
                up_value += turnover
                local_used = True
            elif cur.close < prev.close:
                down_value += turnover
                local_used = True
        usable += int(local_used)
    total = up_value + down_value
    if usable < 5 or total <= 0:
        return None
    return round(_clamp(100.0 * up_value / total), 2)


def derive_crowd_inputs(
    index_candles: Sequence[Candle],
    equity_histories: Mapping[str, Sequence[Candle]],
) -> CrowdInputs:
    """Build R0.8 Crowd inputs from point-in-time trailing market data."""
    return CrowdInputs(
        breadth_sentiment=breadth_sentiment(equity_histories),
        momentum_sentiment=momentum_sentiment(index_candles),
        volume_sentiment=volume_sentiment(equity_histories),
        volatility_sentiment=volatility_sentiment(index_candles),
        positioning_sentiment=None,
    )
