from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReentryState(str, Enum):
    INACTIVE = "INACTIVE"
    CAPITULATION_WATCH = "CAPITULATION_WATCH"
    ACCUMULATION_WATCH = "ACCUMULATION_WATCH"
    RECOVERY_WATCH = "RECOVERY_WATCH"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


@dataclass(frozen=True)
class ReentryInputs:
    """Research-only R1.1 inputs.

    Re-entry is allowed to activate only after a frozen EXIT event. Thresholds are
    predeclared research heuristics and MUST NOT be interpreted as calibrated
    probabilities or production actions.
    """

    sessions_since_exit: int | None
    crash_score: float | None
    critical_confirmations: int | None
    return_5d_pct: float | None
    crash_score_change_5d: float | None


@dataclass(frozen=True)
class ReentryResult:
    state: ReentryState
    reasons: tuple[str, ...]
    production_ready: bool = False


def classify_reentry(inputs: ReentryInputs) -> ReentryResult:
    required = (
        inputs.sessions_since_exit,
        inputs.crash_score,
        inputs.critical_confirmations,
        inputs.return_5d_pct,
        inputs.crash_score_change_5d,
    )
    if any(x is None for x in required):
        return ReentryResult(ReentryState.DATA_INSUFFICIENT, ("required PIT evidence incomplete",))

    since_exit = int(inputs.sessions_since_exit)
    score = float(inputs.crash_score)
    conf = int(inputs.critical_confirmations)
    ret5 = float(inputs.return_5d_pct)
    dscore5 = float(inputs.crash_score_change_5d)

    # Re-entry is not even considered without a recent validated EXIT context.
    if since_exit < 0 or since_exit > 60:
        return ReentryResult(ReentryState.INACTIVE, ("no recent frozen EXIT context",))

    if score >= 75 and conf >= 3 and ret5 <= -5.0:
        return ReentryResult(
            ReentryState.CAPITULATION_WATCH,
            ("extreme crash stress", "3+ confirmations", "5d selloff <= -5%"),
        )

    if score <= 60 and dscore5 <= -15.0 and ret5 >= 0.0:
        return ReentryResult(
            ReentryState.ACCUMULATION_WATCH,
            ("crash stress falling quickly", "5d return stabilized"),
        )

    if score <= 45 and conf <= 1 and dscore5 <= -10.0 and ret5 >= 3.0:
        return ReentryResult(
            ReentryState.RECOVERY_WATCH,
            ("low current crash stress", "few confirmations", "5d rebound >= 3%"),
        )

    return ReentryResult(ReentryState.INACTIVE, ("re-entry confirmation incomplete",))
