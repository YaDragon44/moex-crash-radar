from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ISS_BASE = "https://iss.moex.com/iss"


@dataclass(frozen=True)
class Candle:
    begin: str
    open: float
    close: float
    high: float
    low: float
    value: float | None
    volume: float | None


def _table(payload: dict, name: str) -> list[dict]:
    block = payload.get(name)
    if not isinstance(block, dict):
        raise ValueError(f"missing ISS block: {name}")
    columns = block.get("columns")
    data = block.get("data")
    if not isinstance(columns, list) or not isinstance(data, list):
        raise ValueError(f"invalid ISS block: {name}")
    return [dict(zip(columns, row)) for row in data]


def parse_candles(payload: dict) -> list[Candle]:
    rows = _table(payload, "candles")
    result: list[Candle] = []
    for row in rows:
        required = ("begin", "open", "close", "high", "low")
        if any(row.get(k) is None for k in required):
            continue
        result.append(
            Candle(
                begin=str(row["begin"]),
                open=float(row["open"]),
                close=float(row["close"]),
                high=float(row["high"]),
                low=float(row["low"]),
                value=float(row["value"]) if row.get("value") is not None else None,
                volume=float(row["volume"]) if row.get("volume") is not None else None,
            )
        )
    return result


def _get_json(url: str, timeout: int = 20) -> dict:
    req = Request(url, headers={"User-Agent": "moex-crash-radar/0.3"})
    with urlopen(req, timeout=timeout) as response:  # nosec B310: fixed HTTPS MOEX endpoint
        return json.loads(response.read().decode("utf-8"))


def _fetch_candles(
    market: str,
    secid: str,
    *,
    start: str | None = None,
    end: str | None = None,
    interval: int = 24,
) -> list[Candle]:
    params = {
        "interval": interval,
        "iss.meta": "off",
        "iss.only": "candles",
        "candles.columns": "begin,open,close,high,low,value,volume",
    }
    if start:
        params["from"] = start
    if end:
        params["till"] = end
    url = f"{ISS_BASE}/engines/stock/markets/{market}/securities/{secid}/candles.json?{urlencode(params)}"
    return parse_candles(_get_json(url))


def _fetch_candles_range(
    market: str,
    secid: str,
    *,
    start: str,
    end: str,
    interval: int = 24,
    max_pages: int = 20,
) -> list[Candle]:
    """Fetch a long range without assuming a single ISS response is complete.

    Pagination advances by the last returned candle date. Duplicate dates are
    de-duplicated. The function stops when end is reached or the source returns
    no new rows.
    """
    cursor = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    by_begin: dict[str, Candle] = {}

    for _ in range(max_pages):
        batch = _fetch_candles(
            market,
            secid,
            start=cursor.isoformat(),
            end=end,
            interval=interval,
        )
        if not batch:
            break

        before = len(by_begin)
        for candle in batch:
            by_begin[candle.begin] = candle

        last_day = date.fromisoformat(batch[-1].begin[:10])
        if last_day >= end_date or len(by_begin) == before:
            break
        cursor = last_day + timedelta(days=1)

    return sorted(by_begin.values(), key=lambda c: c.begin)


def fetch_index_candles(
    secid: str = "IMOEX",
    *,
    start: str | None = None,
    end: str | None = None,
    interval: int = 24,
) -> list[Candle]:
    return _fetch_candles("index", secid, start=start, end=end, interval=interval)


def fetch_share_candles(
    secid: str,
    *,
    start: str | None = None,
    end: str | None = None,
    interval: int = 24,
) -> list[Candle]:
    return _fetch_candles("shares", secid, start=start, end=end, interval=interval)


def fetch_index_history(secid: str, *, start: str, end: str) -> list[Candle]:
    return _fetch_candles_range("index", secid, start=start, end=end, interval=24)


def fetch_share_history(secid: str, *, start: str, end: str) -> list[Candle]:
    return _fetch_candles_range("shares", secid, start=start, end=end, interval=24)
