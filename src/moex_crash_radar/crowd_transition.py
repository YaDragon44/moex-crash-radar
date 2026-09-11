from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .crowd import CrowdState


@dataclass(frozen=True)
class CrowdTransition:
    day: str
    raw_state: str
    stable_state: str
    score: float | None
    delta_5: float | None
    falling_fast: bool
    distribution_watch: bool


def stable_states(rows: Sequence[object], *, persistence: int = 3, hysteresis: float = 5.0) -> list[CrowdTransition]:
    """Research-only Crowd transition filter.

    A raw state must persist before becoming stable. Hysteresis prevents a stable
    state from flipping merely because score crosses a boundary by a few points.
    No Crash/EXIT inputs or thresholds are modified here.
    """
    if persistence < 2:
        raise ValueError("persistence must be >= 2")
    out: list[CrowdTransition] = []
    stable = CrowdState.DATA_INSUFFICIENT.value
    candidate: str | None = None
    candidate_count = 0
    scores: list[float | None] = []

    for row in rows:
        raw = str(getattr(row, "state"))
        score = getattr(row, "score")
        scores.append(score)

        desired = raw
        if stable not in (CrowdState.DATA_INSUFFICIENT.value, raw) and score is not None:
            # Hold the current state inside a small boundary buffer.
            bounds = {
                CrowdState.PANIC.value: (None, 20.0 + hysteresis),
                CrowdState.FEAR.value: (20.0 - hysteresis, 40.0 + hysteresis),
                CrowdState.NEUTRAL.value: (40.0 - hysteresis, 60.0 + hysteresis),
                CrowdState.GREED.value: (60.0 - hysteresis, 80.0 + hysteresis),
                CrowdState.EUPHORIA.value: (80.0 - hysteresis, None),
            }
            low, high = bounds.get(stable, (None, None))
            if (low is None or score >= low) and (high is None or score < high):
                desired = stable

        if desired == stable:
            candidate = None
            candidate_count = 0
        elif desired == candidate:
            candidate_count += 1
        else:
            candidate = desired
            candidate_count = 1
        if candidate is not None and candidate_count >= persistence:
            stable = candidate
            candidate = None
            candidate_count = 0

        delta5 = None
        if len(scores) >= 6 and score is not None and scores[-6] is not None:
            delta5 = round(score - scores[-6], 2)
        falling_fast = bool(delta5 is not None and delta5 <= -15.0)

        # Distribution watch is intentionally conservative: price is not used
        # here because this layer only establishes a stable Crowd transition.
        # Cross-engine price/breadth divergence is validated in the replay.
        out.append(CrowdTransition(
            day=str(getattr(row, "day")), raw_state=raw, stable_state=stable,
            score=score, delta_5=delta5, falling_fast=falling_fast,
            distribution_watch=False,
        ))
    return out
