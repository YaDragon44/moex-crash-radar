from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QualityStatus(str, Enum):
    DATA_READY = "DATA_READY"
    PARTIAL = "PARTIAL"
    NO_GO = "NO_GO"


@dataclass(frozen=True)
class SourceCoverage:
    name: str
    expected: int
    present: int

    @property
    def coverage(self) -> float:
        if self.expected <= 0:
            return 0.0
        return max(0.0, min(1.0, self.present / self.expected))


@dataclass(frozen=True)
class QualityReport:
    status: QualityStatus
    coverage: float
    missing_sources: tuple[str, ...]
    point_in_time_safe: bool


def assess_quality(
    sources: list[SourceCoverage],
    *,
    point_in_time_safe: bool,
    minimum_coverage: float = 0.95,
) -> QualityReport:
    """Fail closed: incomplete mandatory evidence cannot produce a backtest GO."""
    if not sources:
        return QualityReport(QualityStatus.NO_GO, 0.0, ("ALL",), point_in_time_safe)

    missing = tuple(source.name for source in sources if source.coverage < minimum_coverage)
    aggregate = sum(source.coverage for source in sources) / len(sources)

    if not point_in_time_safe:
        return QualityReport(QualityStatus.NO_GO, aggregate, missing, False)
    if missing:
        status = QualityStatus.PARTIAL if aggregate >= minimum_coverage else QualityStatus.NO_GO
        return QualityReport(status, aggregate, missing, True)
    return QualityReport(QualityStatus.DATA_READY, aggregate, (), True)
