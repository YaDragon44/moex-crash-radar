from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Sequence

from .history import DailyEvidence


@dataclass(frozen=True)
class GateCandidate:
    score_threshold: float
    confirmations: int
    persistence: int
    max_5d_return_pct: float | None
    signal_events: int
    false_events: int
    false_event_rate: float | None
    detected_episodes: int
    total_episodes: int
    median_lead_days: float | None


def _return_5d(evidence: Sequence[DailyEvidence], index: int) -> float | None:
    if index < 5:
        return None
    base = evidence[index - 5].close
    if base <= 0:
        return None
    return (evidence[index].close / base - 1.0) * 100.0


def _qualifies(
    evidence: Sequence[DailyEvidence],
    index: int,
    score_threshold: float,
    confirmations: int,
    max_5d_return_pct: float | None,
) -> bool:
    row = evidence[index]
    if row.score is None or row.score < score_threshold or row.critical_confirmations < confirmations:
        return False
    if max_5d_return_pct is None:
        return True
    ret5 = _return_5d(evidence, index)
    return ret5 is not None and ret5 <= max_5d_return_pct


def signal_event_indices(
    evidence: Sequence[DailyEvidence],
    *,
    score_threshold: float,
    confirmations: int,
    persistence: int = 1,
    max_5d_return_pct: float | None = None,
) -> list[int]:
    """Return starts of independent EXIT warning events.

    Crash Score is the early-warning regime layer. `max_5d_return_pct` adds a price
    confirmation layer so CASH is not triggered merely because structural risk is
    elevated for a long time while the index is still stable/rising.
    """
    if persistence < 1:
        raise ValueError("persistence must be >= 1")

    events: list[int] = []
    in_event = False
    run = 0
    for i in range(len(evidence)):
        if _qualifies(evidence, i, score_threshold, confirmations, max_5d_return_pct):
            run += 1
            if not in_event and run >= persistence:
                events.append(i)
                in_event = True
        else:
            run = 0
            in_event = False
    return events


def false_event_stats(
    evidence: Sequence[DailyEvidence],
    event_indices: Sequence[int],
    *,
    horizon_rows: int = 20,
    drawdown_threshold_pct: float = -8.0,
) -> tuple[int, int, float | None]:
    evaluated = 0
    false = 0
    for i in event_indices:
        future = evidence[i : i + horizon_rows + 1]
        if len(future) < horizon_rows + 1:
            continue
        evaluated += 1
        base = evidence[i].close
        min_close = min(x.close for x in future)
        dd = (min_close / base - 1.0) * 100.0
        if dd > drawdown_threshold_pct:
            false += 1
    return evaluated, false, round(false / evaluated, 4) if evaluated else None


def episode_detection(
    evidence: Sequence[DailyEvidence],
    event_indices: Sequence[int],
    episodes: Sequence[tuple[str, str, str]],
) -> tuple[int, int, float | None]:
    event_days = [evidence[i].day for i in event_indices]
    leads: list[int] = []
    detected = 0
    valid = 0
    for _name, start, end in episodes:
        rows = [r for r in evidence if start <= r.day <= end]
        if not rows:
            continue
        valid += 1
        trough = min(rows, key=lambda r: r.close)
        hits = [d for d in event_days if start <= d <= trough.day]
        if not hits:
            continue
        detected += 1
        first = hits[0]
        leads.append((datetime.fromisoformat(trough.day) - datetime.fromisoformat(first)).days)
    return detected, valid, round(float(median(leads)), 1) if leads else None


def calibrate_cash_gate(
    evidence: Sequence[DailyEvidence],
    episodes: Sequence[tuple[str, str, str]],
    *,
    thresholds: Sequence[float] = (56, 60, 65, 70),
    confirmations_options: Sequence[int] = (3, 4),
    persistence_options: Sequence[int] = (1, 2, 3),
    max_5d_return_options: Sequence[float | None] = (None, -1.0, -2.0, -3.0, -4.0),
) -> list[GateCandidate]:
    candidates: list[GateCandidate] = []
    for threshold in thresholds:
        for confirmations in confirmations_options:
            for persistence in persistence_options:
                for max_ret5 in max_5d_return_options:
                    events = signal_event_indices(
                        evidence,
                        score_threshold=threshold,
                        confirmations=confirmations,
                        persistence=persistence,
                        max_5d_return_pct=max_ret5,
                    )
                    evaluated, false, false_rate = false_event_stats(evidence, events)
                    detected, total, median_lead = episode_detection(evidence, events, episodes)
                    candidates.append(
                        GateCandidate(
                            score_threshold=threshold,
                            confirmations=confirmations,
                            persistence=persistence,
                            max_5d_return_pct=max_ret5,
                            signal_events=evaluated,
                            false_events=false,
                            false_event_rate=false_rate,
                            detected_episodes=detected,
                            total_episodes=total,
                            median_lead_days=median_lead,
                        )
                    )
    return sorted(
        candidates,
        key=lambda x: (
            -(x.detected_episodes / max(x.total_episodes, 1)),
            x.false_event_rate if x.false_event_rate is not None else 1.0,
            -(x.median_lead_days or 0),
            x.signal_events,
        ),
    )
