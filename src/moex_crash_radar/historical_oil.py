from __future__ import annotations

import csv
import io
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .moex import Candle


FRED_BRENT_SERIES = "DCOILBRENTEU"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def parse_fred_brent_csv(text: str) -> list[Candle]:
    """Parse FRED's daily Europe Brent spot-price CSV into Candle-compatible rows.

    Missing observations ('.' / blank) are skipped. OHLC are intentionally equal
    because FRED publishes one daily spot observation; downstream validation uses
    closes only. No interpolation or synthetic filling is performed.
    """
    reader = csv.DictReader(io.StringIO(text))
    result: list[Candle] = []
    value_column = FRED_BRENT_SERIES
    for row in reader:
        day = (row.get("DATE") or row.get("observation_date") or "").strip()
        raw = (row.get(value_column) or "").strip()
        if not day or not raw or raw == ".":
            continue
        try:
            datetime.strptime(day, "%Y-%m-%d")
            value = float(raw)
        except (ValueError, TypeError):
            continue
        if value <= 0:
            continue
        result.append(Candle(begin=day, open=value, close=value, high=value, low=value, value=None, volume=None))
    return sorted(result, key=lambda c: c.begin)


def fetch_fred_brent_history(*, start: str, end: str, timeout: int = 30) -> list[Candle]:
    """Fetch daily Europe Brent spot history via FRED (underlying EIA series).

    This source is used only for historical validation when MOEX expired-futures
    candles are unavailable. It is not mixed into the live Oil/RUB signal.
    """
    params = {
        "id": FRED_BRENT_SERIES,
        "cosd": start,
        "coed": end,
    }
    req = Request(
        f"{FRED_CSV_URL}?{urlencode(params)}",
        headers={"User-Agent": "moex-crash-radar/0.5.3.1"},
    )
    with urlopen(req, timeout=timeout) as response:  # nosec B310: fixed HTTPS FRED endpoint
        text = response.read().decode("utf-8", errors="replace")
    candles = parse_fred_brent_csv(text)
    if not candles:
        raise ValueError("FRED Brent series returned no usable observations")
    return candles
