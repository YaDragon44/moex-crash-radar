from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

MSK = timezone(timedelta(hours=3))
SNAPSHOT = Path("artifacts/ta_market/current.json")
HISTORY = Path("artifacts/ta_market/signal_history.json")
OUT = Path("artifacts/ta_market/signal_performance.json")
TFS = ("D1", "H1", "M10")


def finite(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def parse_dt(value):
    if not value:
        return None
    text = str(value).replace(" ", "T")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MSK)
    return dt.astimezone(MSK)


def candle_rows(snapshot, ticker, tf):
    raw = (((snapshot.get("securities") or {}).get(ticker) or {}).get("raw") or {}).get(tf) or []
    out = []
    for x in raw:
        dt = parse_dt(x.get("end"))
        if not dt or not all(finite(x.get(k)) for k in ("h", "l", "c")):
            continue
        out.append({"end": dt, "h": float(x["h"]), "l": float(x["l"]), "c": float(x["c"])})
    return out


def evaluate_event(event, candles):
    event_time = parse_dt(event.get("time"))
    direction = event.get("direction")
    if not event_time or direction not in ("LONG", "SHORT"):
        return None
    if not all(finite(event.get(k)) for k in ("entry", "stop", "tp2", "rr")):
        return None

    entry = float(event["entry"])
    stop = float(event["stop"])
    tp2 = float(event["tp2"])
    rr = float(event["rr"])
    after = [c for c in candles if c["end"] > event_time]
    if not after:
        return {
            "ticker": event.get("ticker"), "tf": event.get("tf"), "time": event.get("time"),
            "direction": direction, "entry": entry, "stop": stop, "tp2": tp2, "planned_rr": rr,
            "result": "OPEN", "exit_time": None, "result_r": None,
        }

    for c in after:
        if direction == "LONG":
            hit_stop = c["l"] <= stop
            hit_tp2 = c["h"] >= tp2
        else:
            hit_stop = c["h"] >= stop
            hit_tp2 = c["l"] <= tp2

        if hit_stop and hit_tp2:
            return {
                "ticker": event.get("ticker"), "tf": event.get("tf"), "time": event.get("time"),
                "direction": direction, "entry": entry, "stop": stop, "tp2": tp2, "planned_rr": rr,
                "result": "AMBIGUOUS", "exit_time": c["end"].isoformat(timespec="seconds"), "result_r": None,
            }
        if hit_tp2:
            return {
                "ticker": event.get("ticker"), "tf": event.get("tf"), "time": event.get("time"),
                "direction": direction, "entry": entry, "stop": stop, "tp2": tp2, "planned_rr": rr,
                "result": "WIN", "exit_time": c["end"].isoformat(timespec="seconds"), "result_r": round(rr, 4),
            }
        if hit_stop:
            return {
                "ticker": event.get("ticker"), "tf": event.get("tf"), "time": event.get("time"),
                "direction": direction, "entry": entry, "stop": stop, "tp2": tp2, "planned_rr": rr,
                "result": "LOSS", "exit_time": c["end"].isoformat(timespec="seconds"), "result_r": -1.0,
            }

    return {
        "ticker": event.get("ticker"), "tf": event.get("tf"), "time": event.get("time"),
        "direction": direction, "entry": entry, "stop": stop, "tp2": tp2, "planned_rr": rr,
        "result": "OPEN", "exit_time": None, "result_r": None,
    }


def summarize(items):
    decided = [x for x in items if x["result"] in ("WIN", "LOSS")]
    wins = [x for x in decided if x["result"] == "WIN"]
    losses = [x for x in decided if x["result"] == "LOSS"]
    ambiguous = [x for x in items if x["result"] == "AMBIGUOUS"]
    open_ = [x for x in items if x["result"] == "OPEN"]
    result_rs = [x["result_r"] for x in decided if finite(x.get("result_r"))]
    win_rate = len(wins) / len(decided) if decided else None
    expectancy = sum(result_rs) / len(result_rs) if result_rs else None
    avg_win = sum(x["result_r"] for x in wins) / len(wins) if wins else None
    avg_loss = sum(x["result_r"] for x in losses) / len(losses) if losses else None
    profit_factor = None
    gross_win = sum(x["result_r"] for x in wins)
    gross_loss = abs(sum(x["result_r"] for x in losses))
    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    elif gross_win > 0:
        profit_factor = None
    return {
        "signals": len(items), "closed": len(decided), "wins": len(wins), "losses": len(losses),
        "open": len(open_), "ambiguous": len(ambiguous),
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "avg_win_r": round(avg_win, 4) if avg_win is not None else None,
        "avg_loss_r": round(avg_loss, 4) if avg_loss is not None else None,
        "expectancy_r": round(expectancy, 4) if expectancy is not None else None,
        "profit_factor": round(profit_factor, 4) if profit_factor is not None else None,
    }


def main():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    ready_events = [e for e in history.get("events", []) if e.get("status") == "READY"]
    cache = {}
    evaluated = []
    for e in ready_events:
        key = (e.get("ticker"), e.get("tf"))
        if key[1] not in TFS:
            continue
        cache.setdefault(key, candle_rows(snapshot, key[0], key[1]))
        x = evaluate_event(e, cache[key])
        if x:
            evaluated.append(x)

    by_ticker = {}
    for ticker in sorted({x["ticker"] for x in evaluated if x.get("ticker")}):
        by_ticker[ticker] = summarize([x for x in evaluated if x.get("ticker") == ticker])
    by_tf = {}
    for tf in TFS:
        subset = [x for x in evaluated if x.get("tf") == tf]
        if subset:
            by_tf[tf] = summarize(subset)

    doc = {
        "release": "R0.9.0 Production Observation",
        "generated_at": snapshot.get("generated_at") or datetime.now(MSK).isoformat(timespec="seconds"),
        "definition": "Model signal quality: WIN if TP2 is reached before Stop after READY; LOSS if Stop first; AMBIGUOUS if both occur in one candle and order is unknown. This is not actual account P/L.",
        "summary": summarize(evaluated),
        "by_ticker": by_ticker,
        "by_tf": by_tf,
        "signals": evaluated[-200:],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ready_signals": len(evaluated), **doc["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
