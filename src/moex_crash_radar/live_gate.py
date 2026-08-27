from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Sequence

from .history import DailyEvidence
from .calibration import signal_event_indices


@dataclass(frozen=True)
class ExitGateParams:
    score_threshold: float = 65.0
    early_warning_threshold: float = 56.0
    confirmations: int = 3
    persistence: int = 2
    max_5d_return_pct: float = -3.0
    cooldown_rows: int = 30
    require_breadth_volume: bool = False
    rearm_clear_rows: int = 3


CALIBRATED_EXIT_GATE = ExitGateParams()


def _return_5d(evidence: Sequence[DailyEvidence], index: int) -> float | None:
    if index < 5:
        return None
    base = evidence[index - 5].close
    if base <= 0:
        return None
    return round((evidence[index].close / base - 1.0) * 100.0, 2)


def _latest_qualifies(evidence: Sequence[DailyEvidence], p: ExitGateParams) -> bool:
    if not evidence:
        return False
    i = len(evidence) - 1
    row = evidence[i]
    ret5 = _return_5d(evidence, i)
    if row.score is None or row.score < p.score_threshold:
        return False
    if row.critical_confirmations < p.confirmations:
        return False
    if p.require_breadth_volume:
        if row.breadth_score is None or row.volume_distribution_score is None:
            return False
        if row.breadth_score < 60 or row.volume_distribution_score < 60:
            return False
    return ret5 is not None and ret5 <= p.max_5d_return_pct


def _still_disarmed(evidence: Sequence[DailyEvidence], last_event: int, p: ExitGateParams) -> bool:
    clear_run = 0
    for i in range(last_event + 1, len(evidence)):
        row = evidence[i]
        ret5 = _return_5d(evidence, i)
        qualifies = (
            row.score is not None
            and row.score >= p.score_threshold
            and row.critical_confirmations >= p.confirmations
            and ret5 is not None
            and ret5 <= p.max_5d_return_pct
        )
        if p.require_breadth_volume:
            qualifies = qualifies and row.breadth_score is not None and row.breadth_score >= 60 and row.volume_distribution_score is not None and row.volume_distribution_score >= 60
        if qualifies:
            clear_run = 0
        else:
            clear_run += 1
        if clear_run >= p.rearm_clear_rows and i - last_event > p.cooldown_rows:
            return False
    return True


def exit_gate_status(evidence: Sequence[DailyEvidence], params: ExitGateParams = CALIBRATED_EXIT_GATE) -> dict:
    if not evidence or evidence[-1].score is None:
        return {
            "stage": "DATA_INSUFFICIENT",
            "cash_confirmed": False,
            "latest_5d_return_pct": None,
            "params": asdict(params),
            "last_event_day": None,
        }

    events = signal_event_indices(
        evidence,
        score_threshold=params.score_threshold,
        confirmations=params.confirmations,
        persistence=params.persistence,
        max_5d_return_pct=params.max_5d_return_pct,
        cooldown_rows=params.cooldown_rows,
        require_breadth_volume=params.require_breadth_volume,
        rearm_clear_rows=params.rearm_clear_rows,
    )
    last_event = events[-1] if events else None
    cash_confirmed = last_event is not None and _still_disarmed(evidence, last_event, params)
    latest = evidence[-1]
    ret5 = _return_5d(evidence, len(evidence) - 1)

    if cash_confirmed:
        stage = "CASH_CONFIRMED"
    elif _latest_qualifies(evidence, params):
        stage = "EXIT_WATCH"
    elif latest.score >= params.early_warning_threshold:
        stage = "EARLY_WARNING"
    else:
        stage = "NORMAL"

    return {
        "stage": stage,
        "cash_confirmed": cash_confirmed,
        "latest_5d_return_pct": ret5,
        "params": asdict(params),
        "last_event_day": evidence[last_event].day if last_event is not None else None,
    }
