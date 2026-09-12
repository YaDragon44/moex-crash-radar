from __future__ import annotations

import os

import monitor
from position_manager import (
    format_position_event,
    has_active_position,
    load_state_file,
    manage_position,
    open_position,
    save_state_file,
)
from trade_plan import build_trade_plan, format_trade_plan

_original_format_signal = monitor.format_signal
_original_save_state = monitor.save_state


def _format_signal_r15(signal):
    base = _original_format_signal(signal)
    return base + "\n\n💼 TRADE PLAN\n" + format_trade_plan(signal) + "\n\nДЕЙСТВИЕ: вход только по READY; стоп не расширять."


def _save_state_r15(signal_id: str) -> None:
    state = load_state_file(monitor.STATE_FILE)
    state["last_signal_id"] = signal_id
    pending = _CURRENT_SIGNAL.get("signal")
    if pending is not None and signal_id == pending.get("signal_id"):
        plan = build_trade_plan(pending)
        state["position"] = open_position(pending, plan)
    save_state_file(monitor.STATE_FILE, state)


_CURRENT_SIGNAL: dict[str, object] = {"signal": None}

_original_detect_signal = monitor.detect_signal


def _detect_signal_capture(candles):
    signal = _original_detect_signal(candles)
    _CURRENT_SIGNAL["signal"] = signal
    return signal


monitor.format_signal = _format_signal_r15
monitor.save_state = _save_state_r15
monitor.detect_signal = _detect_signal_capture


def manage_existing_position() -> bool:
    mode = os.getenv("MODE", "run")
    if mode != "run":
        return False

    state = load_state_file(monitor.STATE_FILE)
    if not has_active_position(state):
        return False

    candles = monitor.fetch_candles()
    latest = candles[-1]
    levels = monitor.adaptive_levels(candles)
    updated, event = manage_position(state["position"], latest, levels["avg_range"])
    state["position"] = updated
    save_state_file(monitor.STATE_FILE, state)

    if event:
        monitor.send_telegram(format_position_event(updated, event))
        print(f"position_status={updated['status']} event={event} stop={updated['stop']:.2f}")
    else:
        print(f"position_status={updated['status']} event=NONE stop={updated['stop']:.2f}")
    return True


if __name__ == "__main__":
    if manage_existing_position():
        raise SystemExit(0)
    raise SystemExit(monitor.run())
