from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence


class BubbleState(str, Enum):
    HEALTHY = "HEALTHY"
    WARMING = "WARMING"
    OVERHEATED = "OVERHEATED"
    BUILD_UP = "BUBBLE_BUILD_UP"
    FRAGILE = "FRAGILE"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


BUBBLE_WEIGHTS: Mapping[str, float] = {
    "valuation": 0.20,
    "concentration": 0.15,
    "leverage": 0.15,
    "crowd_euphoria": 0.15,
    "price_stretch": 0.15,
    "breadth_fragility": 0.10,
    "volatility_complacency": 0.10,
}


@dataclass(frozen=True)
class BubbleInputs:
    valuation: float | None = None
    concentration: float | None = None
    leverage: float | None = None
    crowd_euphoria: float | None = None
    price_stretch: float | None = None
    breadth_fragility: float | None = None
    volatility_complacency: float | None = None


@dataclass(frozen=True)
class BubbleResult:
    score: float | None
    state: BubbleState
    coverage: float
    available_groups: int
    velocity: float | None
    persistence: int
    transition: str
    reasons: tuple[str, ...]
    actionable: bool = False


def bubble_state(score: float) -> BubbleState:
    if score < 30:
        return BubbleState.HEALTHY
    if score < 45:
        return BubbleState.WARMING
    if score < 60:
        return BubbleState.OVERHEATED
    if score < 75:
        return BubbleState.BUILD_UP
    return BubbleState.FRAGILE


def _check(value: float) -> float:
    if not 0 <= value <= 100:
        raise ValueError("bubble input must be in [0, 100]")
    return value


def calculate_bubble(inputs: BubbleInputs, history: Sequence[float] = ()) -> BubbleResult:
    weighted = 0.0
    available_weight = 0.0
    groups = 0
    contributions: list[tuple[str, float]] = []
    for key, weight in BUBBLE_WEIGHTS.items():
        value = getattr(inputs, key)
        if value is None:
            continue
        value = _check(value)
        weighted += value * weight
        available_weight += weight
        groups += 1
        contributions.append((key, value))

    # Two gates are deliberately separated:
    # 1) research/scoring gate: four independent groups and >=45% model weight;
    # 2) actionable gate: >=60% model weight.
    # This lets us statistically test honest partial historical proxies without
    # ever presenting them as production-ready Bubble signals.
    if groups < 4 or available_weight < 0.45:
        return BubbleResult(None, BubbleState.DATA_INSUFFICIENT, round(available_weight, 4), groups, None, 0, "N/A", (), False)

    score = round(weighted / available_weight, 2)
    state = bubble_state(score)
    actionable = available_weight >= 0.60
    velocity = round(score - history[-1], 2) if history else None

    persistence = 1
    threshold = 60.0
    if score >= threshold:
        for prior in reversed(history):
            if prior < threshold:
                break
            persistence += 1
    else:
        persistence = 0

    if velocity is None:
        transition = "STABLE"
    elif velocity >= 5:
        transition = "INFLATING_FAST"
    elif velocity >= 1.5:
        transition = "INFLATING"
    elif velocity <= -5:
        transition = "DEFLATING_FAST"
    elif velocity <= -1.5:
        transition = "DEFLATING"
    else:
        transition = "STABLE"

    labels = {
        "valuation": "valuation stretch",
        "concentration": "market concentration",
        "leverage": "leverage build-up",
        "crowd_euphoria": "crowd euphoria",
        "price_stretch": "price acceleration/stretch",
        "breadth_fragility": "breadth deterioration",
        "volatility_complacency": "volatility complacency",
    }
    reasons = tuple(labels[key] for key, _ in sorted(contributions, key=lambda x: x[1], reverse=True)[:3])
    return BubbleResult(score, state, round(available_weight, 4), groups, velocity, persistence, transition, reasons, actionable)
