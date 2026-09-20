from __future__ import annotations

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
