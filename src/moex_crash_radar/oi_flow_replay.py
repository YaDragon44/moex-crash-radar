from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Iterable, Sequence

from .oi_flow_alignment import AlignedFutoi


@dataclass(frozen=True)
class ReplayBar:
    decision_timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None


@dataclass(frozen=True)
class ReplayRow:
    decision_timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    source_moment: str
    source_available_at: str
    total_oi: int
    retail_net: int
    legal_net: int
    delta_total_oi: int | None
    delta_retail_net: int | None
    delta_legal_net: int | None


@dataclass(frozen=True)
class ReplayCoverage:
    price_bars: int
    aligned_rows: int
    missing_futoi: int
    coverage_pct: float
    point_in_time_violations: int
    status: str
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def build_replay_rows(
    price_bars: Sequence[ReplayBar],
    aligned_futoi: Iterable[AlignedFutoi],
) -> tuple[list[ReplayRow], ReplayCoverage]:
    """Join 1H price bars with point-in-time-safe FUTOI features.

    Join key is the decision timestamp (the closed 1H bar timestamp). A row is
    emitted only when a complete FUTOI pair was available by that decision time.
    Missing FUTOI is never forward-filled across the quality gate.
    """
    by_decision = {x.decision_timestamp: x for x in aligned_futoi}
    result: list[ReplayRow] = []
    violations = 0

    for bar in sorted(price_bars, key=lambda x: _dt(x.decision_timestamp)):
        futoi = by_decision.get(bar.decision_timestamp)
        if futoi is None:
            continue
        if _dt(futoi.source_available_at) > _dt(bar.decision_timestamp):
            violations += 1
            continue
        result.append(
            ReplayRow(
                decision_timestamp=bar.decision_timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                source_moment=futoi.source_moment,
                source_available_at=futoi.source_available_at,
                total_oi=futoi.total_oi,
                retail_net=futoi.retail_net,
                legal_net=futoi.legal_net,
                delta_total_oi=futoi.delta_total_oi,
                delta_retail_net=futoi.delta_retail_net,
                delta_legal_net=futoi.delta_legal_net,
            )
        )

    total = len(price_bars)
    aligned = len(result)
    missing = max(total - aligned - violations, 0)
    coverage = round((aligned / total) * 100.0, 2) if total else 0.0

    if total == 0:
        status = "N/A"
        note = "No 1H price bars available."
    elif violations:
        status = "FAIL"
        note = "One or more FUTOI observations were published after decision time."
    elif coverage < 90.0:
        status = "FAIL"
        note = "Point-in-time FUTOI coverage below 90% baseline admission threshold."
    else:
        status = "READY"
        note = "Replay rows satisfy point-in-time join and baseline coverage threshold."

    return result, ReplayCoverage(
        price_bars=total,
        aligned_rows=aligned,
        missing_futoi=missing,
        coverage_pct=coverage,
        point_in_time_violations=violations,
        status=status,
        note=note,
    )
