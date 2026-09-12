from __future__ import annotations

import os
from pathlib import Path

import monitor
import run_r15  # applies R1.5 signal/trade-plan/position-state patches
from position_manager import (
    format_position_event,
    has_active_position,
    load_state_file,
    manage_position,
    save_state_file,
)
from trade_journal import append_record_once, export_csv, format_stats, load_records, stats

JOURNAL_JSONL = Path(os.getenv("JOURNAL_JSONL", "vkco-monitor/state/trade_journal.jsonl"))
JOURNAL_CSV = Path(os.getenv("JOURNAL_CSV", "vkco-monitor/state/trade_journal.csv"))


def manage_existing_position_r16() -> bool:
    if os.getenv("MODE", "run") != "run":
        return False

    state = load_state_file(monitor.STATE_FILE)
    if not has_active_position(state):
        return False

    candles = monitor.fetch_candles()
    latest = candles[-1]
    now = monitor.datetime.now(monitor.MOSCOW)
    if latest.end.date() != now.date() or now - latest.end > monitor.timedelta(minutes=45):
        print("position_status=WAIT reason=STALE_OR_MARKET_CLOSED")
        return True

    levels = monitor.adaptive_levels(candles)
    updated, event = manage_position(state["position"], latest, levels["avg_range"])
    state["position"] = updated
    save_state_file(monitor.STATE_FILE, state)

    if not event:
        print(f"position_status={updated['status']} event=NONE stop={updated['stop']:.2f}")
        return True

    text = format_position_event(updated, event)
    if updated.get("status") in {"CLOSED_PROFIT", "CLOSED_STOP", "MANUAL_EXIT", "INVALIDATED"}:
        record, added = append_record_once(JOURNAL_JSONL, updated)
        export_csv(JOURNAL_JSONL, JOURNAL_CSV)
        journal_stats = stats(load_records(JOURNAL_JSONL))
        result_r_text = f"{record['result_r']:+.2f}R" if record.get("result_r") is not None else "n/a"
        text += (
            "\n\n📒 JOURNAL\n"
            f"P/L: {record['pnl_rub']:+,.0f} ₽ | Result: {result_r_text}\n"
            f"{format_stats(journal_stats)}"
        )
        print(f"journal_added={int(added)} trades={journal_stats['trades']}")

    monitor.send_telegram(text)
    print(f"position_status={updated['status']} event={event} stop={updated['stop']:.2f}")
    return True


if __name__ == "__main__":
    if manage_existing_position_r16():
        raise SystemExit(0)
    raise SystemExit(monitor.run())
