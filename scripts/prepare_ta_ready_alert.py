from __future__ import annotations

import hashlib
import json
from pathlib import Path

HISTORY = Path("artifacts/ta_market/signal_history.json")
STATE = Path("artifacts/ta_market/telegram_state.json")
OUT = Path("artifacts/ta_market/ready_alert.txt")
DASHBOARD = "https://yadragon44.github.io/moex-crash-radar/ta-market/"
MAX_SENT_KEYS = 500


def event_key(e: dict) -> str:
    raw = "|".join(str(e.get(k) or "") for k in (
        "time", "ticker", "tf", "direction", "status", "entry", "stop", "tp1", "tp2", "tp3"
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def fmt(x) -> str:
    if x is None:
        return "N/A"
    try:
        return f"{float(x):.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(x)


def message(events: list[dict]) -> str:
    lines = ["🚨 TA Market Monitor · новый READY"]
    for e in events:
        lines += [
            "",
            f"{e.get('ticker')} · {e.get('tf')} · {e.get('direction')}",
            f"Цена: {fmt(e.get('price'))}",
            f"Entry: {fmt(e.get('entry'))}",
            f"Stop: {fmt(e.get('stop'))}",
            f"TP1/TP2/TP3: {fmt(e.get('tp1'))} / {fmt(e.get('tp2'))} / {fmt(e.get('tp3'))}",
            f"R/R: {fmt(e.get('rr'))}",
            f"Причина: {e.get('reason') or 'Все Safety Gate выполнены'}",
        ]
    lines += ["", f"Дашборд: {DASHBOARD}"]
    return "\n".join(lines)


def main() -> None:
    OUT.unlink(missing_ok=True)
    hist = json.loads(HISTORY.read_text(encoding="utf-8"))
    events = hist.get("events") or []
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {
        "release": "R0.8.2 Telegram READY Alerts",
        "baseline_time": None,
        "sent_event_keys": [],
    }

    # First execution is baseline-only. Never replay historical READY events.
    if not state.get("baseline_time"):
        state["baseline_time"] = hist.get("updated_at")
        state["sent_event_keys"] = [event_key(e) for e in events if e.get("status") == "READY"][-MAX_SENT_KEYS:]
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"mode": "BASELINE", "ready_alerts": 0, "baseline_time": state["baseline_time"]}, ensure_ascii=False))
        return

    sent = set(state.get("sent_event_keys") or [])
    fresh = []
    for e in events:
        if e.get("status") != "READY":
            continue
        k = event_key(e)
        if k not in sent:
            fresh.append(e)
            sent.add(k)

    if fresh:
        OUT.write_text(message(fresh), encoding="utf-8")

    state["baseline_time"] = hist.get("updated_at") or state.get("baseline_time")
    state["sent_event_keys"] = list(sent)[-MAX_SENT_KEYS:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mode": "ACTIVE", "ready_alerts": len(fresh), "message_created": OUT.exists()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
