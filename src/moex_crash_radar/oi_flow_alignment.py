from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .futoi import FutoiPair, is_point_in_time_safe


@dataclass(frozen=True)
class AlignedFutoi:
    decision_timestamp: str
    source_moment: str
    source_available_at: str
    ticker: str
    total_oi: int
    retail_net: int
    legal_net: int
    delta_total_oi: int | None
    delta_retail_net: int | None
    delta_legal_net: int | None


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def pair_available_at(pair: FutoiPair) -> str:
    """Earliest timestamp when the complete FIZ+YUR pair was known."""
    return max(pair.retail.systime, pair.legal.systime)


def latest_safe_pair(
    pairs: Iterable[FutoiPair],
    *,
    ticker: str,
    decision_timestamp: str,
) -> FutoiPair | None:
    """Return latest complete pair published no later than decision time.

    Selection is based on publication time (SYSTIME), not exchange-event MOMENT.
    This prevents the common historical look-ahead error where a snapshot is
    attached to a bar whose close preceded the snapshot's publication.
    """
    decision = _dt(decision_timestamp)
    candidates: list[FutoiPair] = []
    for pair in pairs:
        if pair.ticker.upper() != ticker.upper():
            continue
        if not is_point_in_time_safe(pair, decision_timestamp):
            continue
        if _dt(pair_available_at(pair)) <= decision:
            candidates.append(pair)
    if not candidates:
        return None
    return max(candidates, key=lambda p: _dt(pair_available_at(p)))


def align_decision_times(
    pairs: Iterable[FutoiPair],
    *,
    ticker: str,
    decision_timestamps: Iterable[str],
) -> list[AlignedFutoi]:
    """As-of align 5-minute FUTOI snapshots to closed 1H decision timestamps."""
    materialized = list(pairs)
    result: list[AlignedFutoi] = []
    previous: FutoiPair | None = None

    for decision_timestamp in sorted(decision_timestamps, key=_dt):
        current = latest_safe_pair(
            materialized,
            ticker=ticker,
            decision_timestamp=decision_timestamp,
        )
        if current is None:
            continue

        if previous is None:
            d_oi = d_retail = d_legal = None
        else:
            d_oi = current.total_oi - previous.total_oi
            d_retail = current.retail.net - previous.retail.net
            d_legal = current.legal.net - previous.legal.net

        result.append(
            AlignedFutoi(
                decision_timestamp=decision_timestamp,
                source_moment=current.moment,
                source_available_at=pair_available_at(current),
                ticker=current.ticker,
                total_oi=current.total_oi,
                retail_net=current.retail.net,
                legal_net=current.legal.net,
                delta_total_oi=d_oi,
                delta_retail_net=d_retail,
                delta_legal_net=d_legal,
            )
        )
        previous = current

    return result
