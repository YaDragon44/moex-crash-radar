from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import pstdev
from typing import Sequence

from .bubble import BubbleInputs, BubbleResult
from .bubble_research import calculate_research_bubble
from .history import DailyEvidence


@dataclass(frozen=True)
class HistoricalBubblePoint:
    day: str
    score: float | None
    state: str
    velocity: float | None
    persistence: int
    transition: str
    coverage: float


def _pct_rank(values: Sequence[float], current: float) -> float | None:
    if len(values) < 60:
        return None
    return round(100.0 * sum(v <= current for v in values) / len(values), 2)


def _return(closes: Sequence[float], lookback: int) -> float | None:
    if len(closes) <= lookback or closes[-1 - lookback] <= 0:
        return None
    return (closes[-1] / closes[-1 - lookback] - 1.0) * 100.0


def _vol(closes: Sequence[float], lookback: int = 20) -> float | None:
    if len(closes) <= lookback:
        return None
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(len(closes) - lookback, len(closes)) if closes[i - 1] > 0]
    if len(rets) < lookback:
        return None
    return pstdev(rets) * sqrt(252) * 100.0


def historical_bubble_points(evidence: Sequence[DailyEvidence]) -> list[HistoricalBubblePoint]:
    """Point-in-time research proxy; never a production Dangerous Bubble score."""
    closes: list[float] = []
    vol_history: list[float] = []
    stretch_history: list[float] = []
    bubble_scores: list[float] = []
    out: list[HistoricalBubblePoint] = []

    for row in evidence:
        closes.append(row.close)
        r20 = _return(closes, 20)
        r60 = _return(closes, 60)
        vol20 = _vol(closes, 20)
        if vol20 is not None:
            vol_history.append(vol20)

        stretch_raw = None if r20 is None or r60 is None else 0.6 * r20 + 0.4 * r60
        if stretch_raw is not None:
            stretch_history.append(stretch_raw)
        price_stretch = _pct_rank(stretch_history[-252:], stretch_raw) if stretch_raw is not None else None
        breadth_fragility = row.breadth_score

        concentration_proxy = None
        if breadth_fragility is not None and r20 is not None:
            index_resilience = max(0.0, min(100.0, 50.0 + r20 * 5.0))
            concentration_proxy = round(0.55 * breadth_fragility + 0.45 * index_resilience, 2)

        volatility_complacency = None
        if vol20 is not None and len(vol_history) >= 60 and (r20 is None or r20 >= -3.0):
            vol_rank = _pct_rank(vol_history[-252:], vol20)
            volatility_complacency = None if vol_rank is None else round(100.0 - vol_rank, 2)

        result: BubbleResult = calculate_research_bubble(
            BubbleInputs(
                concentration=concentration_proxy,
                price_stretch=price_stretch,
                breadth_fragility=breadth_fragility,
                volatility_complacency=volatility_complacency,
            ),
            bubble_scores,
        )
        if result.score is not None:
            bubble_scores.append(result.score)
        out.append(HistoricalBubblePoint(row.day, result.score, result.state.value, result.velocity, result.persistence, result.transition, result.coverage))
    return out
