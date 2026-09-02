from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Sequence

from .bubble_history import HistoricalBubblePoint
from .history import DailyEvidence


@dataclass(frozen=True)
class BubbleEpisode:
    name: str
    start: str
    trough: str


@dataclass(frozen=True)
class BubbleValidationResult:
    threshold: float
    warning_events: int
    false_events: int
    false_event_rate: float | None
    detected_episodes: int
    total_episodes: int
    median_lead_days: float | None
    median_advance_vs_exit_days: float | None
    coverage_rate: float
    status: str


def _days(a: str, b: str) -> int:
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days


def _warning_events(points: Sequence[HistoricalBubblePoint], threshold: float, rearm_rows: int = 20) -> list[int]:
    events: list[int] = []
    armed = True
    clear = 0
    for i, point in enumerate(points):
        active = point.score is not None and point.score >= threshold
        if active and armed:
            events.append(i)
            armed = False
            clear = 0
        elif not active and not armed:
            clear += 1
            if clear >= rearm_rows:
                armed = True
                clear = 0
        elif active:
            clear = 0
    return events


def validate_bubble(
    evidence: Sequence[DailyEvidence],
    points: Sequence[HistoricalBubblePoint],
    episodes: Sequence[BubbleEpisode],
    *,
    threshold: float = 60.0,
    forward_rows: int = 60,
    drawdown_threshold_pct: float = -10.0,
    exit_event_days: Sequence[str] = (),
) -> BubbleValidationResult:
    if len(evidence) != len(points):
        raise ValueError("evidence and bubble points must align")
    scored = sum(p.score is not None for p in points)
    coverage = scored / len(points) if points else 0.0
    if coverage < 0.60:
        return BubbleValidationResult(threshold, 0, 0, None, 0, len(episodes), None, None, round(coverage, 4), "DATA_GATE_FAIL_NO_DECISION")

    events = _warning_events(points, threshold)
    false_events = 0
    for i in events:
        future = evidence[i : i + forward_rows + 1]
        if len(future) < 2:
            continue
        min_close = min(row.close for row in future)
        dd = (min_close / evidence[i].close - 1.0) * 100.0
        if dd > drawdown_threshold_pct:
            false_events += 1

    leads: list[int] = []
    advances: list[int] = []
    detected = 0
    for episode in episodes:
        candidates = [points[i].day for i in events if episode.start <= points[i].day <= episode.trough]
        if not candidates:
            continue
        first = candidates[0]
        detected += 1
        leads.append(_days(first, episode.trough))
        prior_exit = [d for d in exit_event_days if episode.start <= d <= episode.trough]
        if prior_exit:
            advances.append(_days(first, prior_exit[0]))

    rate = false_events / len(events) if events else None
    med_lead = median(leads) if leads else None
    med_advance = median(advances) if advances else None

    # Research gate: Bubble Radar must warn before/at EXIT, preserve all known
    # calibration episodes and avoid becoming a permanent false-alarm siren.
    go = (
        detected == len(episodes)
        and med_advance is not None
        and med_advance >= 0
        and rate is not None
        and rate <= 0.40
    )
    status = "GO_FOR_BUBBLE_INTEGRATION_REVIEW" if go else "NO_GO_KEEP_RESEARCH_ONLY"
    return BubbleValidationResult(
        threshold=threshold,
        warning_events=len(events),
        false_events=false_events,
        false_event_rate=None if rate is None else round(rate, 4),
        detected_episodes=detected,
        total_episodes=len(episodes),
        median_lead_days=None if med_lead is None else round(float(med_lead), 1),
        median_advance_vs_exit_days=None if med_advance is None else round(float(med_advance), 1),
        coverage_rate=round(coverage, 4),
        status=status,
    )
