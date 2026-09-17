from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReentryV2State(str, Enum):
    INACTIVE = "INACTIVE"
    CAPITULATION_WATCH = "CAPITULATION_WATCH"
    STABILIZATION_WATCH = "STABILIZATION_WATCH"
    ACCUMULATION_WATCH = "ACCUMULATION_WATCH"
    RECOVERY_WATCH = "RECOVERY_WATCH"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


@dataclass(frozen=True)
class ReentryV2Inputs:
    sessions_since_exit: int | None
    crash_score: float | None
    critical_confirmations: int | None
    return_5d_pct: float | None
    return_10d_pct: float | None
    crash_score_change_5d: float | None
    crash_score_change_10d: float | None


@dataclass(frozen=True)
class ReentryV2Result:
    state: ReentryV2State
    reasons: tuple[str, ...]
    production_ready: bool = False


def classify_reentry_v2(x: ReentryV2Inputs) -> ReentryV2Result:
    """R1.1.3 research candidate: require stabilization before accumulation.

    The redesign intentionally uses only existing PIT market evidence. It does not
    add a new indicator and does not alter the frozen EXIT model.
    """
    required = (
        x.sessions_since_exit,
        x.crash_score,
        x.critical_confirmations,
        x.return_5d_pct,
        x.return_10d_pct,
        x.crash_score_change_5d,
        x.crash_score_change_10d,
    )
    if any(v is None for v in required):
        return ReentryV2Result(ReentryV2State.DATA_INSUFFICIENT, ("required PIT evidence incomplete",))

    since = int(x.sessions_since_exit)
    score = float(x.crash_score)
    conf = int(x.critical_confirmations)
    ret5 = float(x.return_5d_pct)
    ret10 = float(x.return_10d_pct)
    ds5 = float(x.crash_score_change_5d)
    ds10 = float(x.crash_score_change_10d)

    if since < 0 or since > 60:
        return ReentryV2Result(ReentryV2State.INACTIVE, ("no recent frozen EXIT context",))

    if score >= 75 and conf >= 3 and ret5 <= -5.0:
        return ReentryV2Result(
            ReentryV2State.CAPITULATION_WATCH,
            ("extreme crash stress", "3+ confirmations", "5d selloff <= -5%"),
        )

    # First require the acute selloff to stop. This is observation, not a buy signal.
    if score <= 65 and ds5 <= -10.0 and ret5 >= 0.0:
        return ReentryV2Result(
            ReentryV2State.STABILIZATION_WATCH,
            ("crash stress easing", "5d price no longer falling"),
        )

    # Accumulation requires broader 10-session confirmation. This is the key
    # redesign intended to reject short relief rallies such as Jan-2022.
    if (
        since >= 10
        and score <= 50
        and conf <= 1
        and ret5 >= 2.0
        and ret10 >= 0.0
        and ds5 <= -5.0
        and ds10 <= -15.0
    ):
        return ReentryV2Result(
            ReentryV2State.ACCUMULATION_WATCH,
            ("10-session stabilization confirmed", "crash stress materially lower", "few confirmations"),
        )

    if (
        since >= 15
        and score <= 40
        and conf == 0
        and ret5 >= 3.0
        and ret10 >= 5.0
        and ds10 <= -15.0
    ):
        return ReentryV2Result(
            ReentryV2State.RECOVERY_WATCH,
            ("10-session rebound confirmed", "crash stress low", "no critical confirmations"),
        )

    return ReentryV2Result(ReentryV2State.INACTIVE, ("re-entry confirmation incomplete",))
