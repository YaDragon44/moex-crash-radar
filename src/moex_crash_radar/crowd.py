from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CrowdState(str, Enum):
    PANIC = "PANIC"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EUPHORIA = "EUPHORIA"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


@dataclass(frozen=True)
class CrowdInputs:
    breadth_sentiment: float | None = None
    momentum_sentiment: float | None = None
    volume_sentiment: float | None = None
    volatility_sentiment: float | None = None
    positioning_sentiment: float | None = None


@dataclass(frozen=True)
class CrowdResult:
    score: float | None
    state: CrowdState
    coverage: float
    available_groups: int
    velocity: float | None
    direction: str
    extreme: bool | None
    reasons: tuple[str, ...]


# R0.8 research weights only. Positioning is deliberately excluded from the
# production composite until it proves incremental value independently.
WEIGHTS = {
    "breadth_sentiment": .30,
    "momentum_sentiment": .30,
    "volume_sentiment": .20,
    "volatility_sentiment": .20,
}


def crowd_state(score: float) -> CrowdState:
    if score < 20:
        return CrowdState.PANIC
    if score < 40:
        return CrowdState.FEAR
    if score < 60:
        return CrowdState.NEUTRAL
    if score < 80:
        return CrowdState.GREED
    return CrowdState.EUPHORIA


def calculate_crowd(inputs: CrowdInputs, prior_score: float | None = None) -> CrowdResult:
    weighted = available = 0.0
    groups = 0
    contributions: list[tuple[str, float]] = []
    for key, weight in WEIGHTS.items():
        value = getattr(inputs, key)
        if value is None:
            continue
        if not 0 <= value <= 100:
            raise ValueError("crowd input must be in [0, 100]")
        weighted += value * weight
        available += weight
        groups += 1
        contributions.append((key, value))

    # Fail closed: Crowd is not published from one or two indicator groups.
    if groups < 3 or available < .70:
        return CrowdResult(None, CrowdState.DATA_INSUFFICIENT, round(available, 4), groups, None, "N/A", None, ())

    score = round(weighted / available, 2)
    velocity = round(score - prior_score, 2) if prior_score is not None else None
    if velocity is None:
        direction = "STABLE"
    elif velocity >= 5:
        direction = "RISING_FAST"
    elif velocity >= 1.5:
        direction = "RISING"
    elif velocity <= -5:
        direction = "FALLING_FAST"
    elif velocity <= -1.5:
        direction = "FALLING"
    else:
        direction = "STABLE"

    labels = {
        "breadth_sentiment": "market breadth",
        "momentum_sentiment": "price momentum",
        "volume_sentiment": "volume participation",
        "volatility_sentiment": "volatility behaviour",
    }
    reasons = tuple(labels[k] for k, _ in sorted(contributions, key=lambda x: abs(x[1] - 50), reverse=True)[:3])
    return CrowdResult(
        score=score,
        state=crowd_state(score),
        coverage=round(available, 4),
        available_groups=groups,
        velocity=velocity,
        direction=direction,
        extreme=score < 20 or score >= 80,
        reasons=reasons,
    )
