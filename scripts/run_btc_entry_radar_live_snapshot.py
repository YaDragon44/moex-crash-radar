from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.btc_entry_radar_r1_4_0 import EntryRadarInput, to_dict

FGI_URL = "https://api.alternative.me/fng/"
OKX_CANDLES = "https://www.okx.com/api/v5/market/candles"
OKX_OI_HISTORY = "https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history"


def fetch_json(url: str, params: dict) -> dict:
    req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "btc-entry-radar/1.4.0"})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def percentile(values: list[float], q: float) -> float:
    x = sorted(values)
    if not x:
        raise ValueError("empty percentile input")
    pos = (len(x) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return x[lo]
    return x[lo] * (hi - pos) + x[hi] * (pos - lo)


def load_fgi(now: datetime) -> dict:
    p = fetch_json(FGI_URL, {"limit": 2, "format": "json"})
    row = p["data"][0]
    ts = datetime.fromtimestamp(int(row["timestamp"]), tz=timezone.utc)
    age_h = (now - ts).total_seconds() / 3600
    return {"value": float(row["value"]), "classification": row.get("value_classification"), "timestamp": ts.isoformat(), "age_h": age_h, "fresh": age_h <= 48}


def load_candles(now: datetime) -> dict:
    p = fetch_json(OKX_CANDLES, {"instId": "BTC-USDT", "bar": "4H", "limit": 60})
    if p.get("code") != "0":
        raise RuntimeError(f"OKX candles code={p.get('code')} msg={p.get('msg')}")
    rows = []
    for r in p.get("data", []):
        if len(r) < 9 or str(r[8]) != "1":
            continue
        rows.append({"ts": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4])})
    rows.sort(key=lambda z: z["ts"])
    if len(rows) < 20:
        raise RuntimeError(f"only {len(rows)} completed 4H candles")
    latest = rows[-1]
    prev3 = rows[-4:-1]
    prev6 = rows[-7:-1]
    price_confirm = latest["close"] > max(x["high"] for x in prev3)
    new_local_low = latest["low"] < min(x["low"] for x in prev6)
    trs = []
    for i in range(1, len(rows)):
        cur, prev = rows[i], rows[i-1]
        trs.append(max(cur["high"]-cur["low"], abs(cur["high"]-prev["close"]), abs(cur["low"]-prev["close"])))
    atr14 = statistics.fmean(trs[-14:])
    swing_low = min(x["low"] for x in prev6)
    stop = swing_low - 0.5 * atr14
    stop_atr = (latest["close"] - stop) / atr14 if atr14 > 0 else None
    ts = datetime.fromtimestamp(latest["ts"] / 1000, tz=timezone.utc)
    age_h = (now - ts).total_seconds() / 3600
    return {"price": latest["close"], "timestamp": ts.isoformat(), "age_h": age_h, "fresh": age_h <= 8,
            "price_confirm_4h": price_confirm, "new_local_low_4h": new_local_low,
            "atr14_4h": atr14, "swing_low_4h": swing_low, "stop_price": stop, "stop_atr": stop_atr}


def _oi_point(row):
    if isinstance(row, dict):
        ts = row.get("ts")
        val = row.get("oiUsd") or row.get("oiCcy") or row.get("oi")
        return (int(ts), float(val)) if ts is not None and val not in (None, "") else None
    if isinstance(row, list) and len(row) >= 2:
        return int(row[0]), float(row[1])
    return None


def load_oi(now: datetime) -> dict:
    p = fetch_json(OKX_OI_HISTORY, {"instId": "BTC-USDT-SWAP", "period": "4H", "limit": 100})
    if p.get("code") != "0":
        raise RuntimeError(f"OKX OI code={p.get('code')} msg={p.get('msg')}")
    pts = [x for x in (_oi_point(r) for r in p.get("data", [])) if x and x[1] > 0]
    pts = sorted(dict(pts).items())
    if len(pts) < 30:
        raise RuntimeError(f"only {len(pts)} valid OI history points")
    vals = [v for _, v in pts]
    deltas = [vals[i] / vals[i-6] - 1 for i in range(6, len(vals))]
    current_delta = deltas[-1]
    p10, p90 = percentile(deltas, .10), percentile(deltas, .90)
    if current_delta <= p10:
        regime = "DELEVERAGING"
    elif current_delta >= p90 and current_delta > 0:
        regime = "OVERHEATED"
    elif current_delta > 0.03:
        regime = "MODERATE_BUILD"
    else:
        regime = "STABLE"
    ts = datetime.fromtimestamp(pts[-1][0] / 1000, tz=timezone.utc)
    age_h = (now - ts).total_seconds() / 3600
    return {"regime": regime, "timestamp": ts.isoformat(), "age_h": age_h, "fresh": age_h <= 12,
            "oi_value": vals[-1], "delta_24h": current_delta, "delta_p10": p10, "delta_p90": p90, "points": len(vals)}


def main():
    now = datetime.now(timezone.utc)
    errors = {}
    try:
        fgi = load_fgi(now)
    except Exception as e:
        fgi = None; errors["fgi"] = repr(e)
    try:
        market = load_candles(now)
    except Exception as e:
        market = None; errors["market_4h"] = repr(e)
    try:
        oi = load_oi(now)
    except Exception as e:
        oi = None; errors["oi"] = repr(e)

    crowd_ok = bool(fgi and fgi["fresh"])
    price_ok = bool(market and market["fresh"])
    risk_ok = bool(market and market.get("stop_atr") is not None)
    oi_ok = bool(oi and oi["fresh"])
    coverage = 25.0 * sum([crowd_ok, price_ok, risk_ok, oi_ok])
    core_ready = crowd_ok and price_ok and risk_ok

    radar = EntryRadarInput(
        fgi=fgi["value"] if fgi else None,
        price_confirm_4h=market["price_confirm_4h"] if market else None,
        new_local_low_4h=market["new_local_low_4h"] if market else None,
        oi_regime=oi["regime"] if oi_ok else "N/A",
        stop_atr=market["stop_atr"] if market else None,
        data_ready=core_ready,
    )
    out = to_dict(radar)
    out["market"] = market
    out["crowd"] = fgi
    out["open_interest"] = oi
    out["quality"] = {"coverage_pct": coverage, "status": "DATA READY" if core_ready else "PARTIAL",
                      "crowd": "LIVE" if crowd_ok else "N/A", "price_4h": "LIVE" if price_ok else "N/A",
                      "risk": "LIVE" if risk_ok else "N/A", "oi": "LIVE" if oi_ok else "N/A", "errors": errors}
    out["generated_at_utc"] = now.isoformat()
    target = Path("artifacts/btc_entry_radar_live_snapshot.json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
