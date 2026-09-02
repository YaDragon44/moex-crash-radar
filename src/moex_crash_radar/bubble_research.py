from __future__ import annotations

from typing import Sequence

from .bubble import BUBBLE_WEIGHTS, BubbleInputs, BubbleResult, BubbleState, _check, bubble_state


def calculate_research_bubble(inputs: BubbleInputs, history: Sequence[float] = ()) -> BubbleResult:
    """Research-only partial Bubble proxy.

    Allows >=45% model coverage for historical experiments. Results are always
    non-actionable and must never be exposed as a production Dangerous Bubble
    score or used by Risk/Action engines.
    """
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

    if groups < 4 or available_weight < 0.45:
        return BubbleResult(None, BubbleState.DATA_INSUFFICIENT, round(available_weight, 4), groups, None, 0, "N/A", (), False)

    score = round(weighted / available_weight, 2)
    velocity = round(score - history[-1], 2) if history else None
    persistence = 0
    if score >= 60:
        persistence = 1
        for prior in reversed(history):
            if prior < 60:
                break
            persistence += 1

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
    return BubbleResult(score, bubble_state(score), round(available_weight, 4), groups, velocity, persistence, transition, reasons, False)
