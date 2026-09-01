from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class FutoiSnapshot:
    ticker: str
    client_group: str
    position: int
    long: int
    short: int
    long_entities: int
    short_entities: int
    seqnum: int
    moment: str
    systime: str

    @property
    def net(self) -> int:
        # MOEX POS_SHORT is documented/supplied as a signed negative number in
        # FUTOI samples; the net exposure is long + signed short.
        return self.long + self.short


@dataclass(frozen=True)
class FutoiPair:
    ticker: str
    moment: str
    retail: FutoiSnapshot
    legal: FutoiSnapshot

    @property
    def total_oi(self) -> int:
        # FIZ and YUR net positions are counterparties and sum to ~0, therefore
        # total OI must not be calculated by adding their net positions. Gross
        # long contracts across both groups represent one side of open interest.
        return self.retail.long + self.legal.long


_REQUIRED = {
    "TICKER",
    "CLGROUP",
    "POS",
    "POS_LONG",
    "POS_SHORT",
    "POS_LONG_NUM",
    "POS_SHORT_NUM",
    "SEQNUM",
    "MOMENT",
    "SYSTIME",
}


def parse_futoi_rows(rows: Iterable[dict]) -> list[FutoiSnapshot]:
    result: list[FutoiSnapshot] = []
    for row in rows:
        if not _REQUIRED.issubset(row) or any(row[k] is None for k in _REQUIRED):
            continue
        group = str(row["CLGROUP"]).upper()
        if group not in {"FIZ", "YUR"}:
            continue
        result.append(
            FutoiSnapshot(
                ticker=str(row["TICKER"]).upper(),
                client_group=group,
                position=int(row["POS"]),
                long=int(row["POS_LONG"]),
                short=int(row["POS_SHORT"]),
                long_entities=int(row["POS_LONG_NUM"]),
                short_entities=int(row["POS_SHORT_NUM"]),
                seqnum=int(row["SEQNUM"]),
                moment=str(row["MOMENT"]),
                systime=str(row["SYSTIME"]),
            )
        )
    return result


def pair_snapshots(snapshots: Iterable[FutoiSnapshot]) -> list[FutoiPair]:
    grouped: dict[tuple[str, str], dict[str, FutoiSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault((snapshot.ticker, snapshot.moment), {})[snapshot.client_group] = snapshot

    pairs: list[FutoiPair] = []
    for (ticker, moment), groups in sorted(grouped.items()):
        if "FIZ" not in groups or "YUR" not in groups:
            continue
        pairs.append(FutoiPair(ticker=ticker, moment=moment, retail=groups["FIZ"], legal=groups["YUR"]))
    return pairs


def coverage_ratio(expected_moments: Iterable[str], pairs: Iterable[FutoiPair]) -> float:
    expected = set(expected_moments)
    if not expected:
        return 0.0
    present = {pair.moment for pair in pairs}
    return len(expected & present) / len(expected)


def is_point_in_time_safe(pair: FutoiPair, decision_timestamp: str) -> bool:
    """Reject snapshots published after the trading decision timestamp."""
    decision = datetime.fromisoformat(decision_timestamp)
    return all(datetime.fromisoformat(s.systime) <= decision for s in (pair.retail, pair.legal))
