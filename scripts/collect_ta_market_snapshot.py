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
    req = Request(url, headers={"User-Agent": "ta-market-monitor/0.7.2"})
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
        {"iss.meta": "off", "interval": interval, "from": start,
         "candles.columns": "begin,end,open,close,high,low,value,volume"},
    )
    out = []
    for x in table(p, "candles"):
        if x.get("close") is None:
            continue
        out.append({"t": x.get("begin"), "end": x.get("end"), "o": x.get("open"),
                    "h": x.get("high"), "l": x.get("low"), "c": x.get("close"),
                    "v": x.get("volume"), "value": x.get("value")})
    return out


def stock_marketdata(secid: str) -> dict | None:
    p = get_json(
        f"/engines/stock/markets/shares/securities/{secid}.json",
        {"iss.meta": "off", "iss.only": "marketdata",
         "marketdata.columns": "SECID,BOARDID,LAST,OPEN,HIGH,LOW,LASTTOPREVPRICE,VOLTODAY,VALTODAY,UPDATETIME,SYSTIME"},
    )
    rows = table(p, "marketdata")
    return next((x for x in rows if x.get("SECID") == secid and x.get("LAST") is not None), None) or next((x for x in rows if x.get("SECID") == secid), None)


def dividends(secid: str) -> list[dict]:
    try:
        return table(get_json(f"/securities/{secid}/dividends.json", {"iss.meta": "off"}), "dividends")
    except Exception:
        return []


def imoex_history(days: int = 220) -> list[dict]:
    start = (datetime.now(MSK).date() - timedelta(days=days)).isoformat()
    p = get_json(
        "/history/engines/stock/markets/index/securities/IMOEX.json",
        {"iss.meta": "off", "from": start, "history.columns": "TRADEDATE,CLOSE"},
    )
    return [{"d": x.get("TRADEDATE"), "c": x.get("CLOSE")} for x in table(p, "history") if x.get("CLOSE") is not None]


def breadth_tqbr() -> dict:
    p = get_json(
        "/engines/stock/markets/shares/boards/TQBR/securities.json",
        {"iss.meta": "off", "iss.only": "marketdata",
         "marketdata.columns": "SECID,LAST,LASTTOPREVPRICE,UPDATETIME,SYSTIME"},
    )
    rows = [x for x in table(p, "marketdata") if x.get("LAST") is not None and x.get("LASTTOPREVPRICE") is not None]
    adv = sum(1 for x in rows if float(x["LASTTOPREVPRICE"]) > 0)
    dec = sum(1 for x in rows if float(x["LASTTOPREVPRICE"]) < 0)
    flat = len(rows) - adv - dec
    ratio = adv / (adv + dec) if (adv + dec) else None
    stamp = next((x.get("SYSTIME") or x.get("UPDATETIME") for x in reversed(rows) if x.get("SYSTIME") or x.get("UPDATETIME")), None)
    return {"advancers": adv, "decliners": dec, "flat": flat, "total": len(rows), "advance_ratio": ratio, "time": stamp}


def cnyrub() -> dict:
    p = get_json(
        "/engines/currency/markets/selt/securities/CNYRUB_TOM.json",
        {"iss.meta": "off", "iss.only": "marketdata",
         "marketdata.columns": "SECID,BOARDID,LAST,WAPRICE,OPEN,HIGH,LOW,LASTCHANGEPRCNT,UPDATETIME,SYSTIME"},
    )
    rows = table(p, "marketdata")
    row = next((x for x in rows if x.get("LAST") is not None), None) or next((x for x in rows if x.get("WAPRICE") is not None), None)
    if not row:
        raise RuntimeError("CNYRUB_TOM marketdata absent")
    return row


def brent_contract_codes(months: int = 18) -> list[str]:
    now = datetime.now(MSK)
    base = now.year * 12 + (now.month - 1)
    out = []
    for offset in range(months):
        idx = base + offset
        year, month0 = divmod(idx, 12)
        month = month0 + 1
        out.append(f"BR-{month}.{str(year)[-2:]}")
    return out


def nearest_brent() -> dict:
    today = datetime.now(MSK).date()
    candidates: list[tuple[object, dict]] = []
    # Probe deterministic monthly BR codes directly. This avoids relying on the
    # huge FORTS securities collection, whose ISS pagination/order may omit BR
    # contracts from early pages even while the direct contract endpoint works.
    for secid in brent_contract_codes():
        try:
            p = get_json(
                f"/engines/futures/markets/forts/securities/{secid}.json",
                {"iss.meta": "off", "iss.only": "securities,marketdata",
                 "securities.columns": "SECID,LASTTRADEDATE,SHORTNAME",
                 "marketdata.columns": "SECID,LAST,OPEN,HIGH,LOW,LASTCHANGEPRCNT,NUMTRADES,VOLTODAY,VALTODAY,UPDATETIME,SYSTIME"},
                attempts=2,
            )
        except Exception:
            continue
        sec_rows = table(p, "securities")
        md_rows = table(p, "marketdata")
        sec = next((x for x in sec_rows if x.get("SECID") == secid), None)
        md = next((x for x in md_rows if x.get("SECID") == secid and x.get("LAST") is not None), None)
        if not sec or not md or not sec.get("LASTTRADEDATE"):
            continue
        try:
            last_trade = datetime.fromisoformat(str(sec["LASTTRADEDATE"])).date()
        except ValueError:
            continue
        if last_trade < today:
            continue
        md["CONTRACT"] = secid
        md["LASTTRADEDATE"] = str(last_trade)
        candidates.append((last_trade, md))
        # Codes are generated chronologically; first valid live contract is nearest.
        break
    if not candidates:
        raise RuntimeError("active Brent contract not found by direct monthly probing")
    return min(candidates, key=lambda x: x[0])[1]


def main() -> None:
    generated = datetime.now(MSK).isoformat(timespec="seconds")
    payload: dict = {
        "release": "R0.7.2 Simple Market Context",
        "generated_at": generated, "source": "MOEX ISS", "quality": "OK", "context_quality": "OK",
        "securities": {}, "imoex": [],
        "context": {"breadth": None, "cnyrub": None, "brent": None,
                    "event_risk": {"status": "N/A", "reason": "Reliable macro/corporate event calendar is not integrated"}},
        "errors": {}, "context_errors": {},
    }
    try:
        payload["imoex"] = imoex_history()
    except Exception as exc:
        payload["errors"]["IMOEX"] = f"{type(exc).__name__}: {exc}"
    for name, fn in (("BREADTH", breadth_tqbr), ("CNYRUB", cnyrub), ("BRENT", nearest_brent)):
        try:
            payload["context"][name.lower()] = fn()
        except Exception as exc:
            payload["context_errors"][name] = f"{type(exc).__name__}: {exc}"
    if payload["context_errors"]:
        payload["context_quality"] = "PARTIAL"
    for secid in SECURITIES:
        try:
            md = stock_marketdata(secid)
            if not md:
                raise RuntimeError("marketdata absent")
            payload["securities"][secid] = {"marketdata": md,
                "raw": {"D1": candles(secid, 24, 520), "H1": candles(secid, 60, 45), "M10": candles(secid, 10, 8)},
                "div": dividends(secid)}
        except Exception as exc:
            payload["errors"][secid] = f"{type(exc).__name__}: {exc}"
    if payload["errors"]:
        payload["quality"] = "PARTIAL" if payload["securities"] else "ERROR"
    out = Path("artifacts/ta_market/current.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    print(json.dumps({"generated_at": generated, "quality": payload["quality"],
                      "context_quality": payload["context_quality"], "errors": payload["errors"],
                      "context_errors": payload["context_errors"],
                      "brent_contract": (payload["context"].get("brent") or {}).get("CONTRACT")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
