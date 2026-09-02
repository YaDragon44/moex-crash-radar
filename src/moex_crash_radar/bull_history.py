from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .bull_strength import BullInputs, calculate_bull_strength
from .history import DailyEvidence


@dataclass(frozen=True)
class HistoricalBullPoint:
    day: str
    score: float | None
    state: str
    velocity: float | None
    transition: str
    coverage: float


def _ret(closes: Sequence[float], n: int) -> float | None:
    if len(closes) <= n or closes[-1-n] <= 0:
        return None
    return (closes[-1] / closes[-1-n] - 1) * 100


def _health_from_stress(score: float | None) -> float | None:
    return None if score is None else max(0.0, min(100.0, 100.0-score))


def historical_bull_points(evidence: Sequence[DailyEvidence]) -> list[HistoricalBullPoint]:
    """Point-in-time market-strength series; research only until validated."""
    closes: list[float] = []
    prior: float | None = None
    out: list[HistoricalBullPoint] = []
    for row in evidence:
        closes.append(row.close)
        r20, r60 = _ret(closes,20), _ret(closes,60)
        trend = None if r20 is None or r60 is None else max(0,min(100,50+2*r20+1.2*r60))
        momentum = None if r20 is None else max(0,min(100,50+4*r20))
        result = calculate_bull_strength(BullInputs(
            trend=trend,
            breadth_health=_health_from_stress(row.breadth_score),
            momentum=momentum,
            volume_confirmation=_health_from_stress(row.volume_distribution_score),
            volatility_health=_health_from_stress(row.volatility_liquidity_score),
        ), prior)
        if result.score is not None:
            prior=result.score
        out.append(HistoricalBullPoint(row.day,result.score,result.state.value,result.velocity,result.transition,result.coverage))
    return out
