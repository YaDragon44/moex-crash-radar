from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from statistics import median
from typing import Iterable

from .futoi import FutoiPair
from .oi_flow_alignment import align_decision_times


@dataclass(frozen=True)
class CoverageGateResult:
    ticker: str
    paired_snapshots: int
    unique_days: int
    decision_hours: int
    aligned_hours: int
    alignment_coverage_pct: float
    median_publication_lag_sec: float | None
    max_publication_lag_sec: float | None
    missing_hour_pct: float
    status: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def evaluate_coverage_gate(
    *,
    ticker: str,
    pairs: Iterable[FutoiPair],
    decision_timestamps: Iterable[str],
    min_alignment_coverage_pct: float = 95.0,
    max_median_publication_lag_sec: int = 300,
) -> CoverageGateResult:
    pair_list = [p for p in pairs if p.ticker.upper() == ticker.upper()]
    decisions = sorted(set(decision_timestamps), key=_dt)
    unique_days = len({p.moment[:10] for p in pair_list})

    if not pair_list:
        return CoverageGateResult(
            ticker.upper(), 0, 0, len(decisions), 0, 0.0, None, None, 100.0,
            "N/A", "No FUTOI pairs available for ticker.",
        )
    if not decisions:
        return CoverageGateResult(
            ticker.upper(), len(pair_list), unique_days, 0, 0, 0.0, None, None, 0.0,
            "N/A", "No 1H decision timestamps supplied.",
        )

    aligned = align_decision_times(pair_list, ticker=ticker, decision_timestamps=decisions)
    aligned_by_decision = {x.decision_timestamp: x for x in aligned}
    lags: list[float] = []
    for x in aligned:
        lag = (_dt(x.source_available_at) - _dt(x.source_moment)).total_seconds()
        if lag >= 0:
            lags.append(lag)

    coverage = 100.0 * len(aligned_by_decision) / len(decisions)
    missing = 100.0 - coverage
    median_lag = median(lags) if lags else None
    max_lag = max(lags) if lags else None

    if coverage < min_alignment_coverage_pct:
        status = "FAIL"
        reason = f"Alignment coverage {coverage:.2f}% below {min_alignment_coverage_pct:.2f}% gate."
    elif median_lag is None:
        status = "FAIL"
        reason = "Publication lag cannot be measured."
    elif median_lag > max_median_publication_lag_sec:
        status = "FAIL"
        reason = (
            f"Median publication lag {median_lag:.0f}s exceeds "
            f"{max_median_publication_lag_sec}s gate."
        )
    else:
        status = "READY"
        reason = "Coverage and publication-lag gates passed."

    return CoverageGateResult(
        ticker=ticker.upper(),
        paired_snapshots=len(pair_list),
        unique_days=unique_days,
        decision_hours=len(decisions),
        aligned_hours=len(aligned_by_decision),
        alignment_coverage_pct=round(coverage, 2),
        median_publication_lag_sec=round(median_lag, 2) if median_lag is not None else None,
        max_publication_lag_sec=round(max_lag, 2) if max_lag is not None else None,
        missing_hour_pct=round(missing, 2),
        status=status,
        reason=reason,
    )


def full_model_gate(results: Iterable[CoverageGateResult]) -> dict[str, object]:
    rows = list(results)
    ready = [r.ticker for r in rows if r.status == "READY"]
    blocked = [r.ticker for r in rows if r.status != "READY"]
    return {
        "status": "READY" if rows and not blocked else "NO-GO",
        "ready_tickers": ready,
        "blocked_tickers": blocked,
        "quality_coverage_pct": round(100.0 * len(ready) / len(rows), 2) if rows else 0.0,
    }
