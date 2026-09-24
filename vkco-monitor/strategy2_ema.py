from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

STATE_FILE = Path(os.getenv("STRATEGY2_STATE_FILE", "vkco-monitor/state/strategy2_ema_state.json"))
JOURNAL_FILE = Path(os.getenv("STRATEGY2_JOURNAL_JSONL", "vkco-monitor/state/strategy2_ema_journal.jsonl"))


def ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        raise ValueError(f"Need at least {period} values")
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for value in values[1:]:
        out.append(alpha * float(value) + (1.0 - alpha) * out[-1])
    return out


def evaluate(candles: list[Any]) -> dict[str, Any]:
    if len(candles) < 201:
        raise ValueError("Need at least 201 completed M10 candles for EMA50/EMA200 crossover")
    closes = [float(c.close) for c in candles]
    e50, e200 = ema(closes, 50), ema(closes, 200)
    prev50, now50 = e50[-2], e50[-1]
    prev200, now200 = e200[-2], e200[-1]
    signal = "NONE"
    if prev50 <= prev200 and now50 > now200:
        signal = "BUY"
    elif prev50 >= prev200 and now50 < now200:
        signal = "SELL"
    return {
        "strategy": "S2_EMA50_200_M10",
        "candle": candles[-1].end.isoformat(),
        "price": closes[-1],
        "ema50": round(now50, 4),
        "ema200": round(now200, 4),
        "signal": signal,
    }


def _load_state(path: Path = STATE_FILE) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, Any], path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_journal(path: Path = JOURNAL_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _append_once(record: dict[str, Any], path: Path = JOURNAL_FILE) -> bool:
    if any(r.get("event_id") == record["event_id"] for r in load_journal(path)):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True


def run_shadow(candles: list[Any]) -> dict[str, Any]:
    snap = evaluate(candles)
    state = _load_state()
    signal = snap["signal"]
    event_id = f"{snap['strategy']}:{signal}:{snap['candle']}"
    changed = False

    if signal == "BUY" and not state.get("position"):
        record = {**snap, "event_id": event_id, "action": "OPEN_LONG"}
        changed = _append_once(record)
        if changed:
            state = {"position": {"entry": snap["price"], "opened_at": snap["candle"]}, "last_event_id": event_id}
            _save_state(state)
    elif signal == "SELL" and state.get("position"):
        pos = state["position"]
        entry = float(pos["entry"])
        result_pct = (float(snap["price"]) / entry - 1.0) * 100.0 if entry else None
        record = {
            **snap, "event_id": event_id, "action": "CLOSE_LONG",
            "entry": entry, "opened_at": pos.get("opened_at"),
            "exit": snap["price"], "result_pct": round(result_pct, 3) if result_pct is not None else None,
        }
        changed = _append_once(record)
        if changed:
            state = {"position": None, "last_event_id": event_id}
            _save_state(state)

    return {**snap, "position": state.get("position"), "journal_appended": changed}


def public_snapshot(candles: list[Any]) -> dict[str, Any]:
    snap = evaluate(candles)
    state = _load_state()
    rows = load_journal()
    closed = [r for r in rows if r.get("action") == "CLOSE_LONG"]
    wins = [r for r in closed if float(r.get("result_pct") or 0) > 0]
    return {
        **snap,
        "mode": "SHADOW",
        "position": state.get("position"),
        "closed_trades": len(closed),
        "wins": len(wins),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "journal": rows[-20:],
    }
