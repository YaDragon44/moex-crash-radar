from __future__ import annotations

from datetime import date

from .context_validation import _fetch_generic_history
from .moex import ISS_BASE, Candle


def fetch_brent_history(*, start: str, end: str) -> list[Candle]:
    """Build a long Brent proxy from archived September MOEX futures.

    Expired futures are not guaranteed to remain addressable through the live
    RFUD board endpoint. For historical validation we therefore query the FORTS
    market-level candles endpoint first, with RFUD board only as a fallback.
    Missing contracts are skipped; callers must apply an explicit data gate.
    """
    first_year = date.fromisoformat(start).year
    last_year = date.fromisoformat(end).year + 1
    by_day: dict[str, Candle] = {}

    for year in range(first_year, last_year + 1):
        secid = f"BR-9.{str(year)[-2:]}"
        endpoints = (
            f"{ISS_BASE}/engines/futures/markets/forts/securities/{secid}/candles.json",
            f"{ISS_BASE}/engines/futures/markets/forts/boards/RFUD/securities/{secid}/candles.json",
        )
        candles: list[Candle] = []
        for url in endpoints:
            try:
                candles = _fetch_generic_history(url, start=start, end=end, max_pages=12)
            except Exception:
                candles = []
            if candles:
                break
        for candle in candles:
            by_day[candle.begin[:10]] = candle

    return sorted(by_day.values(), key=lambda c: c.begin)
