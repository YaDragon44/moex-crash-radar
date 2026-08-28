from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .engine import DataQuality, Signal


CONTEXT_WEIGHTS: Mapping[str, float] = {
    "rate_ofz": 0.35,
    "oil_rub": 0.25,
    "macro_earnings": 0.25,
    "news_geopolitics": 0.15,
}


class ContextState(str, Enum):
    SUPPORTIVE = "SUPPORTIVE"
    NEUTRAL = "NEUTRAL"
    CAUTION = "CAUTION"
    STRESS = "STRESS"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


@dataclass(frozen=True)
class ContextResult:
    score: float | None
    state: ContextState
    quality: DataQuality
    coverage: float
    available_groups: int
    total_groups: int


def context_state(score: float) -> ContextState:
    if score < 30:
        return ContextState.SUPPORTIVE
    if score < 55:
        return ContextState.NEUTRAL
    if score < 75:
        return ContextState.CAUTION
    return ContextState.STRESS


def calculate_context(signals: Mapping[str, Signal]) -> ContextResult:
    """Aggregate external macro/context stress independently from Crowd Score.

    A context score is an explainable relative stress composite, not a probability.
    The layer fails closed unless at least two independent groups and >=50% of
    configured weight are usable. STALE/ERROR/N/A inputs never contribute.
    """
    weighted = 0.0
    available_weight = 0.0
    available_groups = 0
    qualities: list[DataQuality] = []

    for key, weight in CONTEXT_WEIGHTS.items():
        signal = signals.get(key)
        if signal is None or signal.quality not in {DataQuality.LIVE, DataQuality.DELAYED}:
            continue
        weighted += signal.score * weight
        available_weight += weight
        available_groups += 1
        qualities.append(signal.quality)

    coverage = round(available_weight, 4)
    if available_groups < 2 or available_weight < 0.50:
        return ContextResult(
            score=None,
            state=ContextState.DATA_INSUFFICIENT,
            quality=DataQuality.NA,
            coverage=coverage,
            available_groups=available_groups,
            total_groups=len(CONTEXT_WEIGHTS),
        )

    score = round(weighted / available_weight, 2)
    quality = DataQuality.DELAYED if DataQuality.DELAYED in qualities else DataQuality.LIVE
    return ContextResult(
        score=score,
        state=context_state(score),
        quality=quality,
        coverage=coverage,
        available_groups=available_groups,
        total_groups=len(CONTEXT_WEIGHTS),
    )
