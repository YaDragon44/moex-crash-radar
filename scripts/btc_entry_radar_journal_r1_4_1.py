from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT = Path("artifacts/btc_entry_radar_live_snapshot.json")
JOURNAL = Path("evidence/btc_entry_radar_journal.csv")
TRANSITIONS = Path("artifacts/btc_entry_radar_transition.json")

FIELDS = [
    "generated_at_utc", "state", "action", "fgi", "price", "price_confirm_4h",
    "new_local_low_4h", "oi_regime", "oi_delta_24h", "stop_atr",
    "quality_coverage_pct", "quality_status"
]

POSITIVE = {"WATCH", "ARMED", "LONG_READY", "MANAGE"}


def row_from_snapshot(p: dict) -> dict:
    return {
        "generated_at_utc": p["generated_at_utc"],
        "state": p["output"]["state"],
        "action": p["output"]["action"],
        "fgi": p.get("crowd", {}).get("value"),
        "price": p.get("market", {}).get("price"),
        "price_confirm_4h": p.get("market", {}).get("price_confirm_4h"),
        "new_local_low_4h": p.get("market", {}).get("new_local_low_4h"),
        "oi_regime": p.get("open_interest", {}).get("regime") if p.get("open_interest") else "N/A",
        "oi_delta_24h": p.get("open_interest", {}).get("delta_24h") if p.get("open_interest") else None,
        "stop_atr": p.get("market", {}).get("stop_atr"),
        "quality_coverage_pct": p.get("quality", {}).get("coverage_pct"),
        "quality_status": p.get("quality", {}).get("status"),
    }


def read_rows() -> list[dict]:
    if not JOURNAL.exists():
        return []
    with JOURNAL.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_if_new(row: dict) -> tuple[list[dict], bool]:
    rows = read_rows()
    key = row["generated_at_utc"]
    if any(r.get("generated_at_utc") == key for r in rows):
        return rows, False
    JOURNAL.parent.mkdir(exist_ok=True)
    write_header = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(row)
    rows.append({k: str(row.get(k, "")) for k in FIELDS})
    return rows, True


def main():
    p = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    row = row_from_snapshot(p)
    if row["state"] in POSITIVE and row["quality_status"] != "DATA READY":
        raise SystemExit("positive transition blocked: Quality Gate is not DATA READY")
    old_rows = read_rows()
    prev_state = old_rows[-1]["state"] if old_rows else None
    rows, appended = append_if_new(row)
    transition = bool(prev_state and prev_state != row["state"])
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_time": row["generated_at_utc"],
        "previous_state": prev_state,
        "current_state": row["state"],
        "transition": transition,
        "positive_transition": transition and row["state"] in POSITIVE,
        "journal_rows": len(rows),
        "appended": appended,
        "quality_status": row["quality_status"],
        "quality_coverage_pct": row["quality_coverage_pct"],
    }
    TRANSITIONS.parent.mkdir(exist_ok=True)
    TRANSITIONS.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
