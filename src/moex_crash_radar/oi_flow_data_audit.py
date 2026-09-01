from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class AuditStatus(str, Enum):
    READY = "READY"
    DELAYED = "DELAYED"
    PARTIAL = "PARTIAL"
    N_A = "N/A"
    FAIL = "FAIL"


@dataclass(frozen=True)
class DatasetAudit:
    instrument: str
    dataset: str
    status: AuditStatus
    granularity: str
    history_from: str | None
    history_to: str | None
    event_time_semantics: str
    available_time_semantics: str
    coverage_pct: float | None = None
    notes: str = ""

    @property
    def backtest_usable(self) -> bool:
        return self.status in {AuditStatus.READY, AuditStatus.DELAYED} and self.coverage_pct not in {0.0}


@dataclass(frozen=True)
class InstrumentAudit:
    instrument: str
    datasets: tuple[DatasetAudit, ...]

    def dataset(self, name: str) -> DatasetAudit | None:
        return next((d for d in self.datasets if d.dataset == name), None)

    @property
    def core_price_ready(self) -> bool:
        row = self.dataset("OHLCV_1H")
        return bool(row and row.backtest_usable)

    @property
    def oi_ready(self) -> bool:
        row = self.dataset("OI_INTRADAY")
        return bool(row and row.backtest_usable)

    @property
    def participant_intraday_ready(self) -> bool:
        row = self.dataset("PARTICIPANT_INTRADAY")
        return bool(row and row.backtest_usable)

    @property
    def participant_daily_ready(self) -> bool:
        row = self.dataset("PARTICIPANT_DAILY")
        return bool(row and row.backtest_usable)

    def supported_models(self) -> tuple[str, ...]:
        models: list[str] = []
        if self.core_price_ready:
            models.extend(["M0", "M1"])
        if self.core_price_ready and self.oi_ready:
            models.append("M2")
        if self.core_price_ready and self.oi_ready and self.participant_intraday_ready:
            models.extend(["M3", "M4"])
        if self.core_price_ready:
            models.append("M5")
        if {"M0", "M1", "M2", "M3", "M4", "M5"}.issubset(models):
            models.append("FULL")
        return tuple(models)


def quality_coverage(rows: Iterable[DatasetAudit]) -> float:
    items = list(rows)
    if not items:
        return 0.0
    weights = {
        AuditStatus.READY: 1.0,
        AuditStatus.DELAYED: 0.8,
        AuditStatus.PARTIAL: 0.5,
        AuditStatus.N_A: 0.0,
        AuditStatus.FAIL: 0.0,
    }
    return round(100.0 * sum(weights[r.status] for r in items) / len(items), 1)


def validate_no_lookahead(row: DatasetAudit) -> None:
    if not row.event_time_semantics.strip():
        raise ValueError(f"{row.instrument}/{row.dataset}: missing event_time semantics")
    if not row.available_time_semantics.strip():
        raise ValueError(f"{row.instrument}/{row.dataset}: missing available_time semantics")
    if row.dataset == "PARTICIPANT_DAILY" and "next" not in row.available_time_semantics.lower():
        raise ValueError(
            f"{row.instrument}/{row.dataset}: daily participant data must explicitly state next-use timing"
        )


def baseline_public_audit(instrument: str) -> InstrumentAudit:
    """Conservative R1.3.1 audit from verified MOEX public/documented semantics.

    MOEX confirms FUTOI history exists from 2020 and updates at five-minute
    granularity, but access is subscription/API-key based. Until an actual export
    is obtained and per-instrument coverage/timestamps pass QA, intraday FUTOI is
    PARTIAL rather than READY and cannot enable M2-M4/FULL.
    """
    rows = (
        DatasetAudit(
            instrument, "OHLCV_1H", AuditStatus.READY, "1H", None, None,
            "MOEX candle interval begin/end for a concrete FORTS contract",
            "usable only after the 1H candle is closed",
            notes="Public ISS supports concrete-contract candles; rollover must be handled explicitly.",
        ),
        DatasetAudit(
            instrument, "OI_DAILY_CONTRACT", AuditStatus.READY, "1D", None, None,
            "exchange end-of-session open interest for a concrete contract",
            "usable after the corresponding session result is published",
            notes="MOEX derivatives archive exposes contract OI in daily market results.",
        ),
        DatasetAudit(
            instrument, "OI_INTRADAY", AuditStatus.PARTIAL, "5m", "2020", None,
            "FUTOI market moment; exact export fields must be verified",
            "requires verified publication/system timestamp from the subscribed export",
            notes="Historical 5-minute FUTOI capability is confirmed by MOEX; actual instrument coverage not yet fetched in this environment.",
        ),
        DatasetAudit(
            instrument, "PARTICIPANT_DAILY", AuditStatus.DELAYED, "1D", None, None,
            "aggregated individuals/legal entities across expiries; daily change versus previous trading day",
            "use only from the next trading decision after publication; never backfill into prior intraday bars",
            notes="Valid as delayed context, not as a replacement for historical intraday FUTOI.",
        ),
        DatasetAudit(
            instrument, "PARTICIPANT_INTRADAY", AuditStatus.PARTIAL, "5m", "2020", None,
            "FUTOI FIZ/YUR long/short snapshots; exact export schema must be verified",
            "requires verified publication/system timestamp from the subscribed export",
            notes="MOEX confirms FUTOI covers individuals/legal entities and history from 2020; access is subscription/API-key based.",
        ),
    )
    for row in rows:
        validate_no_lookahead(row)
    return InstrumentAudit(instrument=instrument, datasets=rows)
