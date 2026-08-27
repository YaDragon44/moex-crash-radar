from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Iterable
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


def fetch_index_candles(
    secid: str = "IMOEX",
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
    url = f"{ISS_BASE}/engines/stock/markets/index/securities/{secid}/candles.json?{urlencode(params)}"
    return parse_candles(_get_json(url))
