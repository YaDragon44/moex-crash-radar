from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT = Path("artifacts/btc_entry_radar_live_snapshot.json")
JOURNAL = Path("evidence/btc_entry_radar_production_journal.csv")
TRANSITION = Path("web/btc-entry-radar/data/transition.json")

FIELDS = [
    "generated_at_utc", "state", "action", "fgi", "price",
    "price_confirm_4h", "new_local_low_4h", "oi_regime", "oi_delta_24h",
    "stop_atr", "quality_coverage_pct", "quality_status", "why"
]
POSITIVE = {"WATCH", "ARMED", "LONG_READY", "MANAGE"}
CONFIRM_REQUIRED = 2


def row_from_snapshot(p: dict) -> dict:
    return {
        "generated_at_utc": p["generated_at_utc"],
        "state": p["output"]["state"],
        "action": p["output"]["action"],
        "fgi": p.get("crowd", {}).get("value"),
        "price": p.get("market", {}).get("price"),
        "price_confirm_4h": p.get("market", {}).get("price_confirm_4h"),
        "new_local_low_4h": p.get("market", {}).get("new_local_low_4h"),
        "oi_regime": (p.get("open_interest") or {}).get("regime", "N/A"),
        "oi_delta_24h": (p.get("open_interest") or {}).get("delta_24h"),
        "stop_atr": p.get("market", {}).get("stop_atr"),
        "quality_coverage_pct": p.get("quality", {}).get("coverage_pct"),
        "quality_status": p.get("quality", {}).get("status"),
        "why": " | ".join(p.get("output", {}).get("why", [])),
    }


def read_rows() -> list[dict]:
    if not JOURNAL.exists():
        return []
    with JOURNAL.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_if_new(row: dict) -> tuple[list[dict], bool]:
    rows = read_rows()
    if any(r.get("generated_at_utc") == row["generated_at_utc"] for r in rows):
        return rows, False
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    write_header = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(row)
    rows.append({k: str(row.get(k, "")) for k in FIELDS})
    return rows, True


def load_previous_confirmed_state() -> str:
    if not TRANSITION.exists():
        return "NO_TRADE"
    try:
        old = json.loads(TRANSITION.read_text(encoding="utf-8"))
        return old.get("confirmed_state") or old.get("current_state") or "NO_TRADE"
    except Exception:
        return "NO_TRADE"


def confirm_state(raw_state: str, previous_rows: list[dict], previous_confirmed: str) -> tuple[str, int, bool]:
    """Return confirmed state, consecutive raw count, pending flag.

    Protective NO_TRADE is immediate. Any non-NO_TRADE state must appear in
    two consecutive snapshots before it becomes the confirmed decision state.
    """
    if raw_state == "NO_TRADE":
        return "NO_TRADE", 1, False

    count = 1
    for r in reversed(previous_rows):
        if r.get("state") == raw_state:
            count += 1
        else:
            break

    if count >= CONFIRM_REQUIRED:
        return raw_state, count, False
    return previous_confirmed, count, True


def main() -> None:
    p = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    row = row_from_snapshot(p)
    if row["state"] in POSITIVE and row["quality_status"] != "DATA READY":
        raise SystemExit("positive state blocked: Quality Gate is not DATA READY")

    old_rows = read_rows()
    prev_raw_state = old_rows[-1]["state"] if old_rows else None
    previous_confirmed = load_previous_confirmed_state()
    confirmed_state, confirmation_count, pending = confirm_state(
        row["state"], old_rows, previous_confirmed
    )

    rows, appended = append_if_new(row)
    raw_transition = bool(prev_raw_state and prev_raw_state != row["state"])
    confirmed_transition = previous_confirmed != confirmed_state

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_time": row["generated_at_utc"],
        "previous_state": prev_raw_state,
        "current_state": row["state"],
        "raw_state": row["state"],
        "previous_confirmed_state": previous_confirmed,
        "confirmed_state": confirmed_state,
        "confirmation_count": confirmation_count,
        "confirmation_required": CONFIRM_REQUIRED,
        "pending_confirmation": pending,
        "transition": raw_transition,
        "positive_transition": bool(raw_transition and row["state"] in POSITIVE),
        "confirmed_transition": confirmed_transition,
        "confirmed_positive_transition": bool(confirmed_transition and confirmed_state in POSITIVE),
        "journal_rows": len(rows),
        "appended": appended,
        "quality_status": row["quality_status"],
        "quality_coverage_pct": row["quality_coverage_pct"],
    }
    TRANSITION.parent.mkdir(parents=True, exist_ok=True)
    TRANSITION.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
