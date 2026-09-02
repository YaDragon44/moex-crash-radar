from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BullState(str, Enum):
    WEAK = "WEAK"
    HEALTHY = "HEALTHY"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


@dataclass(frozen=True)
class BullInputs:
    trend: float | None = None
    breadth_health: float | None = None
    momentum: float | None = None
    volume_confirmation: float | None = None
    volatility_health: float | None = None


@dataclass(frozen=True)
class BullResult:
    score: float | None
    state: BullState
    coverage: float
    available_groups: int
    velocity: float | None
    transition: str
    reasons: tuple[str, ...]


WEIGHTS = {
    "trend": .25,
    "breadth_health": .25,
    "momentum": .20,
    "volume_confirmation": .15,
    "volatility_health": .15,
}


def bull_state(score: float) -> BullState:
    if score < 30:
        return BullState.WEAK
    if score < 55:
        return BullState.HEALTHY
    if score < 75:
        return BullState.STRONG
    return BullState.VERY_STRONG


def calculate_bull_strength(inputs: BullInputs, prior_score: float | None = None) -> BullResult:
    weighted = available = 0.0
    groups = 0
    contributions: list[tuple[str, float]] = []
    for key, weight in WEIGHTS.items():
        value = getattr(inputs, key)
        if value is None:
            continue
        if not 0 <= value <= 100:
            raise ValueError("bull input must be in [0, 100]")
        weighted += value * weight
        available += weight
        groups += 1
        contributions.append((key, value))
    if groups < 3 or available < .60:
        return BullResult(None, BullState.DATA_INSUFFICIENT, round(available, 4), groups, None, "N/A", ())
    score = round(weighted / available, 2)
    velocity = round(score - prior_score, 2) if prior_score is not None else None
    if velocity is None:
        transition = "STABLE"
    elif velocity >= 5:
        transition = "STRENGTHENING_FAST"
    elif velocity >= 1.5:
        transition = "STRENGTHENING"
    elif velocity <= -5:
        transition = "WEAKENING_FAST"
    elif velocity <= -1.5:
        transition = "WEAKENING"
    else:
        transition = "STABLE"
    labels = {
        "trend": "trend structure",
        "breadth_health": "healthy breadth",
        "momentum": "positive momentum",
        "volume_confirmation": "volume confirmation",
        "volatility_health": "contained volatility",
    }
    reasons = tuple(labels[k] for k, _ in sorted(contributions, key=lambda x: x[1], reverse=True)[:3])
    return BullResult(score, bull_state(score), round(available, 4), groups, velocity, transition, reasons)


def bull_bubble_regime(bull_score: float | None, bubble_score: float | None) -> str:
    if bull_score is None or bubble_score is None:
        return "DATA_INSUFFICIENT"
    # Evaluate overlapping states from highest danger to lowest danger.
    if bull_score < 40 and bubble_score >= 60:
        return "BUBBLE_BREAKDOWN_RISK"
    if bull_score < 60 and bubble_score >= 75:
        return "FRAGILE_BULL_DISTRIBUTION_WATCH"
    if bull_score >= 70 and bubble_score >= 60:
        return "BULL_WITH_BUBBLE_BUILD_UP"
    if bull_score >= 75 and bubble_score < 45:
        return "HEALTHY_STRONG_BULL"
    if bull_score >= 55:
        return "RISK_ON"
    return "NEUTRAL_OR_WEAK"
