from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ISS_BASE = "https://iss.moex.com/iss"
SECURITIES = ("SBERP", "VKCO", "OZPH")
MSK = timezone(timedelta(hours=3))


def get_json(path: str, params: dict | None = None, attempts: int = 3, timeout: int = 20) -> dict:
    query = urlencode(params or {})
    url = f"{ISS_BASE}{path}" + (f"?{query}" if query else "")
    req = Request(url, headers={"User-Agent": "ta-market-monitor/0.6.2"})
    last: Exception | None = None
    for i in range(attempts):
        try:
            with urlopen(req, timeout=timeout) as r:  # nosec B310: fixed MOEX HTTPS host
                return json.loads(r.read().decode("utf-8"))
        except HTTPError as exc:
            last = exc
            if exc.code < 500 and exc.code not in (408, 429):
                raise
        except (URLError, TimeoutError, OSError) as exc:
            last = exc
        if i + 1 < attempts:
            time.sleep(2**i)
    assert last is not None
    raise last


def table(payload: dict, name: str) -> list[dict]:
    block = payload.get(name) or {}
    cols, data = block.get("columns"), block.get("data")
    if not isinstance(cols, list) or not isinstance(data, list):
        return []
    return [dict(zip(cols, row)) for row in data]


def candles(secid: str, interval: int, days: int) -> list[dict]:
    start = (datetime.now(MSK).date() - timedelta(days=days)).isoformat()
    p = get_json(
        f"/engines/stock/markets/shares/securities/{secid}/candles.json",
        {
            "iss.meta": "off",
            "interval": interval,
            "from": start,
            "candles.columns": "begin,end,open,close,high,low,value,volume",
        },
    )
    out = []
    for x in table(p, "candles"):
        if x.get("close") is None:
            continue
        out.append({
            "t": x.get("begin"), "end": x.get("end"),
            "o": x.get("open"), "h": x.get("high"), "l": x.get("low"), "c": x.get("close"),
            "v": x.get("volume"), "value": x.get("value"),
        })
    return out


def marketdata(secid: str) -> dict | None:
    p = get_json(
        f"/engines/stock/markets/shares/securities/{secid}.json",
        {
            "iss.meta": "off", "iss.only": "marketdata",
            "marketdata.columns": "SECID,BOARDID,LAST,OPEN,HIGH,LOW,LASTTOPREVPRICE,VOLTODAY,VALTODAY,UPDATETIME,SYSTIME",
        },
    )
    rows = table(p, "marketdata")
    return next((x for x in rows if x.get("SECID") == secid and x.get("LAST") is not None), None) or next((x for x in rows if x.get("SECID") == secid), None)


def dividends(secid: str) -> list[dict]:
    try:
        p = get_json(f"/securities/{secid}/dividends.json", {"iss.meta": "off"})
        return table(p, "dividends")
    except Exception:
        return []


def imoex_history(days: int = 220) -> list[dict]:
    start = (datetime.now(MSK).date() - timedelta(days=days)).isoformat()
    p = get_json(
        "/history/engines/stock/markets/index/securities/IMOEX.json",
        {"iss.meta": "off", "from": start, "history.columns": "TRADEDATE,CLOSE"},
    )
    return [{"d": x.get("TRADEDATE"), "c": x.get("CLOSE")} for x in table(p, "history") if x.get("CLOSE") is not None]


def main() -> None:
    generated = datetime.now(MSK).isoformat(timespec="seconds")
    payload: dict = {
        "release": "R0.6.2 Live Data Snapshot",
        "generated_at": generated,
        "source": "MOEX ISS",
        "quality": "OK",
        "securities": {},
        "imoex": [],
        "errors": {},
    }

    try:
        payload["imoex"] = imoex_history()
    except Exception as exc:
        payload["errors"]["IMOEX"] = f"{type(exc).__name__}: {exc}"

    for secid in SECURITIES:
        try:
            md = marketdata(secid)
            if not md:
                raise RuntimeError("marketdata absent")
            payload["securities"][secid] = {
                "marketdata": md,
                "raw": {
                    "D1": candles(secid, 24, 520),
                    "H1": candles(secid, 60, 45),
                    "M10": candles(secid, 10, 8),
                },
                "div": dividends(secid),
            }
        except Exception as exc:
            payload["errors"][secid] = f"{type(exc).__name__}: {exc}"

    if payload["errors"]:
        payload["quality"] = "PARTIAL" if payload["securities"] else "ERROR"

    out = Path("artifacts/ta_market/current.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    print(json.dumps({"generated_at": generated, "quality": payload["quality"], "errors": payload["errors"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
