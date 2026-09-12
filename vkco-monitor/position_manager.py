from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ACTIVE_STATUSES = {"OPEN", "TP1", "TP2", "TRAILING"}
CLOSED_STATUSES = {"CLOSED_PROFIT", "CLOSED_STOP", "MANUAL_EXIT", "INVALIDATED"}


def load_state_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state_file(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def has_active_position(state: dict[str, Any]) -> bool:
    p = state.get("position") or {}
    return p.get("status") in ACTIVE_STATUSES


def open_position(signal: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": "VKCO",
        "direction": "LONG",
        "status": "OPEN",
        "signal_id": signal["signal_id"],
        "opened_at": signal["time"],
        "entry": float(signal["entry"]),
        "stop": float(signal["stop"]),
        "tp1": float(signal["tp1"]),
        "tp2": float(signal["tp2"]),
        "tp3": float(signal["tp3"]),
        "shares": plan.get("shares"),
        "lots": plan.get("lots"),
        "initial_risk_rub": plan.get("actual_risk"),
        "setup": signal.get("setup"),
        "score": signal.get("score"),
        "last_event": "OPEN",
        "last_price": float(signal["price"]),
    }


def manage_position(position: dict[str, Any], candle: Any, avg_range: float) -> tuple[dict[str, Any], str | None]:
    p = deepcopy(position)
    status = p.get("status")
    if status not in ACTIVE_STATUSES:
        return p, None

    p["last_price"] = float(candle.close)

    # Conservative OHLC handling: if stop and target may both have been touched
    # inside one candle, assume the stop happened first.
    if float(candle.low) <= float(p["stop"]):
        p["status"] = "CLOSED_STOP"
        p["last_event"] = "CLOSED_STOP"
        p["closed_at"] = candle.end.isoformat()
        p["exit_price"] = float(p["stop"])
        return p, "CLOSED_STOP"

    if float(candle.high) >= float(p["tp3"]):
        p["status"] = "CLOSED_PROFIT"
        p["last_event"] = "CLOSED_PROFIT"
        p["closed_at"] = candle.end.isoformat()
        p["exit_price"] = float(p["tp3"])
        return p, "CLOSED_PROFIT"

    if status in {"OPEN", "TP1"} and float(candle.high) >= float(p["tp2"]):
        p["status"] = "TRAILING"
        p["last_event"] = "TP2"
        p["stop"] = max(float(p["stop"]), float(p["tp1"]))
        return p, "TP2"

    if status == "OPEN" and float(candle.high) >= float(p["tp1"]):
        p["status"] = "TP1"
        p["last_event"] = "TP1"
        p["stop"] = max(float(p["stop"]), float(p["entry"]))
        return p, "TP1"

    if status in {"TP2", "TRAILING"}:
        p["status"] = "TRAILING"
        new_stop = float(candle.close) - max(float(avg_range) * 1.5, 0.30)
        if new_stop > float(p["stop"]):
            p["stop"] = round(new_stop, 2)
            p["last_event"] = "TRAILING"
            return p, "TRAILING"

    return p, None


def format_position_event(position: dict[str, Any], event: str) -> str:
    if event == "TP1":
        action = "TP1 достигнут. Стоп переносится в безубыток. Частичную фиксацию можно рассмотреть вручную."
    elif event == "TP2":
        action = "TP2 достигнут. Стоп поднимается не ниже TP1, остаток позиции — в trailing."
    elif event == "TRAILING":
        action = f"Trailing stop подтянут до {position['stop']:.2f} ₽. Стоп не расширять."
    elif event == "CLOSED_PROFIT":
        action = "TP3 достигнут. Позиция считается закрытой по плану."
    elif event == "CLOSED_STOP":
        action = "Стоп достигнут. Позиция считается закрытой, повторный вход только по новому READY."
    else:
        action = event

    return (
        f"📌 VKCO — {position['status']}\n\n"
        f"Entry: {position['entry']:.2f} ₽\n"
        f"Current/last: {position['last_price']:.2f} ₽\n"
        f"Stop: {position['stop']:.2f} ₽\n"
        f"TP1/TP2/TP3: {position['tp1']:.2f} / {position['tp2']:.2f} / {position['tp3']:.2f} ₽\n"
        f"Shares: {position.get('shares') or 'n/a'}\n\n"
        f"ДЕЙСТВИЕ: {action}"
    )
