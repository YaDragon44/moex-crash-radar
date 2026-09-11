from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

MSK = timezone(timedelta(hours=3))
TICKERS = ("SBERP", "VKCO", "OZPH")
TFS = ("D1", "H1", "M10")
SNAPSHOT = Path("artifacts/ta_market/current.json")
HISTORY = Path("artifacts/ta_market/signal_history.json")
MAX_EVENTS = 500


def finite(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def avg(values):
    values = [float(x) for x in values if finite(x)]
    return sum(values) / len(values) if values else None


def ema(values, n):
    if not values:
        return []
    k = 2 / (n + 1)
    out = [float(values[0])]
    for x in values[1:]:
        out.append(float(x) * k + out[-1] * (1 - k))
    return out


def rsi(values, n=14):
    if len(values) < n + 1:
        return None
    g = l = 0.0
    for i in range(len(values) - n, len(values)):
        d = float(values[i]) - float(values[i - 1])
        if d > 0:
            g += d
        else:
            l -= d
    if l == 0:
        return 100.0
    rs = (g / n) / (l / n)
    return 100 - 100 / (1 + rs)


def macd_hist(values):
    if len(values) < 26:
        return None
    a, b = ema(values, 12), ema(values, 26)
    m = [a[i] - b[i] for i in range(len(values))]
    s = ema(m, 9)
    return m[-1] - s[-1]


def pivots(candles, w=2):
    hi, lo = [], []
    for i in range(w, len(candles) - w):
        h_ok = all(j == i or candles[j]["h"] < candles[i]["h"] for j in range(i - w, i + w + 1))
        l_ok = all(j == i or candles[j]["l"] > candles[i]["l"] for j in range(i - w, i + w + 1))
        if h_ok:
            hi.append((i, candles[i]["h"]))
        if l_ok:
            lo.append((i, candles[i]["l"]))
    return hi, lo


def structure(candles):
    hi, lo = pivots(candles)
    trend, label = "RANGE", "mixed"
    if len(hi) >= 2 and len(lo) >= 2:
        if hi[-1][1] > hi[-2][1] and lo[-1][1] > lo[-2][1]:
            trend, label = "BULL", "HH / HL"
        elif hi[-1][1] < hi[-2][1] and lo[-1][1] < lo[-2][1]:
            trend, label = "BEAR", "LH / LL"
    return {
        "trend": trend,
        "label": label,
        "last_high": hi[-1][1] if hi else None,
        "last_low": lo[-1][1] if lo else None,
        "highs": hi,
        "lows": lo,
    }


def rvol(candles):
    if len(candles) < 21:
        return None
    base = avg([x.get("v") for x in candles[-21:-1]])
    return (candles[-1].get("v") or 0) / base if base else None


def profile(candles, bins=24):
    a = candles[-120:]
    if len(a) < 10:
        return None
    low, high = min(x["l"] for x in a), max(x["h"] for x in a)
    step = (high - low) / bins or 1
    vols = [0.0] * bins
    for x in a:
        tp = (x["h"] + x["l"] + x["c"]) / 3
        idx = min(bins - 1, max(0, int((tp - low) / step)))
        vols[idx] += x.get("v") or 0
    ranked = sorted(range(bins), key=lambda i: vols[i], reverse=True)
    level = lambda i: low + (i + 0.5) * step
    return {"poc": level(ranked[0]), "hvn": [level(i) for i in ranked[:4]], "lvn": [level(i) for i in ranked[-4:]], "lo": low, "hi": high}


def fib(candles):
    a = candles[-80:]
    if len(a) < 10:
        return None
    high, low = max(x["h"] for x in a), min(x["l"] for x in a)
    r = high - low
    return {"hi": high, "lo": low, "f382": high-r*.382, "f50": high-r*.5, "f618": high-r*.618, "f786": high-r*.786, "e127": high+r*.272, "e161": high+r*.618}


def candle_gate(candle, tf, now):
    end = candle.get("end")
    if not end:
        return False, False
    text = str(end).replace(" ", "T")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return False, False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MSK)
    age = (now - dt.astimezone(MSK)).total_seconds() / 60
    limit = {"M10": 30, "H1": 120, "D1": 2160}[tf]
    return age >= .5, 0 <= age <= limit


def market_state(snapshot):
    imo = snapshot.get("imoex") or []
    imoex_trend = "N/A"
    if len(imo) >= 21 and finite(imo[-21].get("c")) and finite(imo[-1].get("c")) and float(imo[-21]["c"]):
        ret = (float(imo[-1]["c"]) / float(imo[-21]["c"]) - 1) * 100
        imoex_trend = "BULL" if ret > 1 else "BEAR" if ret < -1 else "RANGE"
    br = ((snapshot.get("context") or {}).get("breadth") or {})
    ratio = br.get("advance_ratio")
    breadth = "N/A"
    if finite(ratio):
        ratio = float(ratio)
        breadth = "BULL" if ratio >= .55 else "BEAR" if ratio <= .45 else "RANGE"
    return imoex_trend, breadth


def target_levels(st, fi, pr, direction, entry):
    z = [st.get("last_high"), st.get("last_low")]
    if fi:
        z += list(fi.values())
    if pr:
        z += [pr.get("poc"), *pr.get("hvn", []), *pr.get("lvn", [])]
    z += [x[1] for x in st.get("highs", [])[-8:]] + [x[1] for x in st.get("lows", [])[-8:]]
    vals = sorted({round(float(v), 4) for v in z if finite(v)}, reverse=(direction == "SHORT"))
    vals = [v for v in vals if (v > entry if direction == "LONG" else v < entry)]
    return vals[:3]


def analyze(snapshot, ticker, tf, now):
    raw = (((snapshot.get("securities") or {}).get(ticker) or {}).get("raw") or {}).get(tf) or []
    c = []
    for x in raw:
        if all(finite(x.get(k)) for k in ("h", "l", "c")):
            c.append({"end": x.get("end"), "h": float(x["h"]), "l": float(x["l"]), "c": float(x["c"]), "v": float(x.get("v") or 0)})
    if not c:
        return {"ticker": ticker, "tf": tf, "direction": "NEUTRAL", "status": "WAIT", "reason": "NO DATA"}

    st = structure(c)
    closes = [x["c"] for x in c]
    e20 = ema(closes, 20)[-1]
    hist = macd_hist(closes)
    r = rsi(closes)
    rv = rvol(c)
    pr, fi = profile(c), fib(c)
    closed, fresh = candle_gate(c[-1], tf, now)
    p = c[-1]["c"]

    if st["trend"] == "RANGE":
        return {"ticker": ticker, "tf": tf, "direction": "NEUTRAL", "status": "WAIT", "reason": "Нет направленной структуры", "price": p}

    direction = "SHORT" if st["trend"] == "BEAR" else "LONG"
    entry = max(st.get("last_high") or p, e20) if direction == "LONG" else min(st.get("last_low") or p, e20)
    if direction == "LONG":
        stop = min(st.get("last_low") or (fi or {}).get("f618") or p, (fi or {}).get("f618") or p)
    else:
        stop = max(st.get("last_high") or (fi or {}).get("f382") or p, (fi or {}).get("f382") or p)
    risk = abs(entry - stop)
    tg = target_levels(st, fi, pr, direction, entry)
    tp1 = tg[0] if len(tg) > 0 else None
    tp2 = tg[1] if len(tg) > 1 else None
    tp3 = tg[2] if len(tg) > 2 else None
    rr = abs(tp2-entry)/risk if tp2 is not None and risk > 0 else None
    price_ok = p > entry if direction == "LONG" else p < entry
    momentum = finite(hist) and finite(r) and ((hist > 0 and r < 75) if direction == "LONG" else (hist < 0 and r > 25))
    rv_ok = finite(rv) and rv > 1.1
    targets_ok = len(tg) >= 2
    rr_ok = finite(rr) and rr >= 2
    imoex, breadth = market_state(snapshot)
    market_ok = not ((direction == "LONG" and imoex == "BEAR" and breadth == "BEAR") or (direction == "SHORT" and imoex == "BULL" and breadth == "BULL"))

    invalid = (direction == "LONG" and p < stop) or (direction == "SHORT" and p > stop)
    status = "INVALID" if invalid else "READY" if all((closed, fresh, price_ok, momentum, rv_ok, targets_ok, rr_ok, market_ok)) else "WAIT"
    if status == "INVALID": reason = "Структурная инвалидация"
    elif status == "READY": reason = "Все Safety Gate выполнены"
    elif not closed: reason = "FORMING candle"
    elif not fresh: reason = "STALE data"
    elif not price_ok: reason = "Нет price trigger"
    elif not rv_ok: reason = "RVOL ≤ 1.1x / N/A"
    elif not targets_ok: reason = "Нет 2 рыночных целей"
    elif not rr_ok: reason = "R/R < 2"
    elif not market_ok: reason = "IMOEX + breadth против сделки"
    else: reason = "Momentum filter"

    def rnd(x): return round(float(x), 4) if finite(x) else None
    return {"ticker": ticker, "tf": tf, "direction": direction, "status": status, "reason": reason,
            "price": rnd(p), "entry": rnd(entry), "stop": rnd(stop), "tp1": rnd(tp1), "tp2": rnd(tp2), "tp3": rnd(tp3), "rr": rnd(rr)}


def fingerprint(x):
    keys = ("direction", "status", "reason", "entry", "stop", "tp1", "tp2", "tp3")
    return tuple(x.get(k) for k in keys)


def main():
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    now = datetime.now(MSK)
    if HISTORY.exists():
        doc = json.loads(HISTORY.read_text(encoding="utf-8"))
    else:
        doc = {"release": "R0.8.1 Signal History", "updated_at": None, "events": []}
    events = doc.setdefault("events", [])
    latest = {}
    for e in events:
        latest[(e.get("ticker"), e.get("tf"))] = e
    added = 0
    for ticker in TICKERS:
        for tf in TFS:
            cur = analyze(snap, ticker, tf, now)
            prev = latest.get((ticker, tf))
            if prev is None or fingerprint(prev) != fingerprint(cur):
                cur["time"] = snap.get("generated_at") or now.isoformat(timespec="seconds")
                events.append(cur)
                latest[(ticker, tf)] = cur
                added += 1
    doc["release"] = "R0.8.1 Signal History"
    doc["updated_at"] = snap.get("generated_at") or now.isoformat(timespec="seconds")
    doc["events"] = events[-MAX_EVENTS:]
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"history_events": len(doc["events"]), "added": added, "updated_at": doc["updated_at"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
