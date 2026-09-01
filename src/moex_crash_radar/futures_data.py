from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import urlencode

from .moex import ISS_BASE, Candle, _get_json, parse_candles


def fetch_futures_candles(
    secid: str,
    *,
    start: str | None = None,
    end: str | None = None,
    interval: int = 60,
) -> list[Candle]:
    """Fetch candles for one concrete MOEX FORTS contract."""
    params: dict[str, str | int] = {
        "interval": interval,
        "iss.meta": "off",
        "iss.only": "candles",
        "candles.columns": "begin,open,close,high,low,value,volume",
    }
    if start:
        params["from"] = start
    if end:
        params["till"] = end
    query = urlencode(params)
    url = f"{ISS_BASE}/engines/futures/markets/forts/securities/{secid}/candles.json?{query}"
    return parse_candles(_get_json(url))


def fetch_futures_history(
    secid: str,
    *,
    start: str,
    end: str,
    interval: int = 60,
    chunk_days: int = 10,
) -> list[Candle]:
    """Fetch a date range in bounded chunks and deduplicate by candle begin.

    Chunking avoids silently treating an ISS response limit as full historical
    coverage. A continuous futures series is deliberately NOT created here;
    callers must supply one concrete contract at a time.
    """
    cursor = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    by_begin: dict[str, Candle] = {}

    while cursor <= end_date:
        chunk_end = min(cursor + timedelta(days=max(chunk_days, 1) - 1), end_date)
        batch = fetch_futures_candles(
            secid,
            start=cursor.isoformat(),
            end=chunk_end.isoformat(),
            interval=interval,
        )
        for candle in batch:
            by_begin[candle.begin] = candle
        cursor = chunk_end + timedelta(days=1)

    return sorted(by_begin.values(), key=lambda c: c.begin)
