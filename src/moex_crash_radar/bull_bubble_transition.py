from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .bull_history import HistoricalBullPoint
from .bubble_history import HistoricalBubblePoint


@dataclass(frozen=True)
class BullBubbleTransition:
    day: str
    bull: float | None
    bubble: float | None
    spread: float | None
    state: str


def build_bull_bubble_transitions(bull: Sequence[HistoricalBullPoint], bubble: Sequence[HistoricalBubblePoint]) -> list[BullBubbleTransition]:
    bmap = {p.day: p for p in bubble}
    out: list[BullBubbleTransition] = []
    for p in bull:
        q = bmap.get(p.day)
        if q is None or p.score is None or q.score is None:
            out.append(BullBubbleTransition(p.day, p.score, None if q is None else q.score, None, "DATA_INSUFFICIENT"))
            continue
        spread = round(p.score - q.score, 2)
        # Overlapping states are evaluated from highest danger to lowest.
        if p.score < 40 and q.score >= 60:
            state = "BREAKDOWN_RISK"
        elif p.score < 60 and q.score >= 75:
            state = "DISTRIBUTION_WATCH"
        elif p.score >= 70 and q.score >= 60:
            state = "BUBBLE_BUILD_UP"
        elif p.score >= 70 and q.score < 45:
            state = "HEALTHY_STRONG_BULL"
        elif q.score >= 60 and p.transition in {"WEAKENING", "WEAKENING_FAST"}:
            state = "BULL_BUBBLE_DIVERGENCE"
        else:
            state = "NEUTRAL"
        out.append(BullBubbleTransition(p.day, p.score, q.score, spread, state))
    return out
