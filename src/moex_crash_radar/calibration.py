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
    signal_events: int
    false_events: int
    false_event_rate: float | None
    detected_episodes: int
    total_episodes: int
    median_lead_days: float | None


def _qualifies(row: DailyEvidence, score_threshold: float, confirmations: int) -> bool:
    return row.score is not None and row.score >= score_threshold and row.critical_confirmations >= confirmations


def signal_event_indices(
    evidence: Sequence[DailyEvidence], *, score_threshold: float, confirmations: int, persistence: int = 1
) -> list[int]:
    """Return starts of independent warning events.

    A persistent risk regime produces one event, not one false-positive observation per
    trading day. `persistence` is the number of consecutive qualifying evidence rows
    required before the event is emitted.
    """
    if persistence < 1:
        raise ValueError("persistence must be >= 1")

    events: list[int] = []
    in_event = False
    run = 0
    for i, row in enumerate(evidence):
        if _qualifies(row, score_threshold, confirmations):
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
) -> list[GateCandidate]:
    candidates: list[GateCandidate] = []
    for threshold in thresholds:
        for confirmations in confirmations_options:
            for persistence in persistence_options:
                events = signal_event_indices(
                    evidence,
                    score_threshold=threshold,
                    confirmations=confirmations,
                    persistence=persistence,
                )
                evaluated, false, false_rate = false_event_stats(evidence, events)
                detected, total, median_lead = episode_detection(evidence, events, episodes)
                candidates.append(
                    GateCandidate(
                        score_threshold=threshold,
                        confirmations=confirmations,
                        persistence=persistence,
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
        ),
    )
