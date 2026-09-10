from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from moex_crash_radar.positioning import fetch_futoi

TICKER = "MX"
EVENTS = (
    "2020-02-28",
    "2021-07-20",
    "2021-11-23",
    "2022-01-17",
    "2022-04-11",
    "2022-06-03",
    "2022-09-21",
    "2024-05-28",
    "2024-08-21",
    "2024-10-28",
    "2025-03-28",
    "2025-09-16",
    "2026-06-10",
)
WINDOW_DAYS = 20
CHUNK_DAYS = 3


def latest_by_day(rows):
    out = {}
    for row in rows:
        key = (row.day, row.client_group)
        cur = out.get(key)
        rank = ((row.moment or ""), row.seqnum if row.seqnum is not None else -1)
        if cur is None:
            out[key] = row
        else:
            cur_rank = ((cur.moment or ""), cur.seqnum if cur.seqnum is not None else -1)
            if rank > cur_rank:
                out[key] = row
    return out


def fetch_window(center_day: str):
    center = date.fromisoformat(center_day)
    start = center - timedelta(days=WINDOW_DAYS)
    end = center + timedelta(days=WINDOW_DAYS)
    rows = []
    cursor = start
    calls = 0
    errors = []
    while cursor <= end:
        till = min(cursor + timedelta(days=CHUNK_DAYS - 1), end)
        try:
            rows.extend(fetch_futoi(TICKER, start=cursor.isoformat(), end=till.isoformat()))
        except Exception as exc:
            errors.append({"from": cursor.isoformat(), "till": till.isoformat(), "error": f"{type(exc).__name__}: {exc}"})
        calls += 1
        cursor = till + timedelta(days=1)
    return rows, calls, errors


def main() -> None:
    event_results = []
    total_calls = 0
    total_errors = 0
    events_with_any_data = 0
    events_with_fiz_yur = 0

    for event_day in EVENTS:
        rows, calls, errors = fetch_window(event_day)
        total_calls += calls
        total_errors += len(errors)
        daily = latest_by_day(rows)
        days = sorted({day for day, _ in daily})
        paired_days = [d for d in days if (d, "FIZ") in daily and (d, "YUR") in daily]
        if days:
            events_with_any_data += 1
        if paired_days:
            events_with_fiz_yur += 1
        event_results.append({
            "event_day": event_day,
            "raw_rows": len(rows),
            "unique_days": len(days),
            "paired_fiz_yur_days": len(paired_days),
            "first_day": days[0] if days else None,
            "last_day": days[-1] if days else None,
            "api_calls": calls,
            "errors": errors,
        })

    event_coverage = events_with_fiz_yur / len(EVENTS)
    # This audit is a source-availability gate only. It does not assign a weight to positioning.
    status = "GO_FOR_RESEARCH" if event_coverage >= 0.80 else ("PARTIAL" if event_coverage > 0 else "NO_DATA")

    payload = {
        "release": "R0.7.1 Historical Positioning Audit",
        "ticker": TICKER,
        "scope": "source availability around frozen EXIT events",
        "source": "MOEX ISS analyticalproducts/futoi",
        "methodology": {
            "event_count": len(EVENTS),
            "window_days_each_side": WINDOW_DAYS,
            "chunk_days": CHUNK_DAYS,
            "intraday_selection": "latest record per day and client group by moment/seqnum",
            "no_threshold_refit": True,
            "no_crash_score_change": True,
        },
        "quality_gate": {
            "status": status,
            "events_with_any_data": events_with_any_data,
            "events_with_paired_fiz_yur": events_with_fiz_yur,
            "event_coverage": round(event_coverage, 4),
            "api_calls": total_calls,
            "failed_calls": total_errors,
            "research_gate_min_event_coverage": 0.80,
        },
        "events": event_results,
        "decision_rule": "Positioning can proceed to incremental-value research only if historical FIZ+YUR coverage is sufficient. It remains outside production Crash/EXIT regardless of this audit result.",
    }
    out = Path("artifacts/positioning_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
