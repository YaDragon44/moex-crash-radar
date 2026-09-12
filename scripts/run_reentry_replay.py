from __future__ import annotations

import json
from pathlib import Path

from moex_crash_radar.reentry import ReentryInputs, ReentryState, classify_reentry

CALIBRATION_TROUGHS = {
    "COVID_2020": "2020-03-18",
    "FEB_2022": "2022-02-24",
    "SEP_2022": "2022-10-10",
    "CORRECTION_2024": "2024-09-03",
}


def _pct(a: float, b: float) -> float:
    return (b / a - 1.0) * 100.0


def _forward_stats(rows, i: int, horizon: int = 20):
    if i + horizon >= len(rows):
        return None
    entry = float(rows[i]["close"])
    future = [float(x["close"]) for x in rows[i : i + horizon + 1]]
    return {
        "forward_20row_min_return_pct": round(_pct(entry, min(future)), 2),
        "forward_20row_max_return_pct": round(_pct(entry, max(future)), 2),
        "forward_20row_end_return_pct": round(_pct(entry, future[-1]), 2),
    }


def main() -> None:
    payload = json.loads(Path("artifacts/historical_evidence.json").read_text(encoding="utf-8"))
    rows = payload.get("daily_evidence") or []
    event_days = payload.get("frozen_exit_validation", {}).get("event_days") or []
    event_set = set(event_days)
    if len(rows) < 500 or not event_days:
        raise SystemExit("R1.1.1 requires PIT daily evidence and frozen EXIT event days")

    last_exit_i = None
    replay = []
    for i, row in enumerate(rows):
        if row["day"] in event_set:
            last_exit_i = i
        since = None if last_exit_i is None else i - last_exit_i
        ret5 = None
        dscore5 = None
        if i >= 5 and row.get("close") is not None and rows[i - 5].get("close") is not None:
            ret5 = _pct(float(rows[i - 5]["close"]), float(row["close"]))
        if i >= 5 and row.get("score") is not None and rows[i - 5].get("score") is not None:
            dscore5 = float(row["score"]) - float(rows[i - 5]["score"])

        result = classify_reentry(ReentryInputs(
            sessions_since_exit=since,
            crash_score=row.get("score"),
            critical_confirmations=row.get("critical_confirmations"),
            return_5d_pct=ret5,
            crash_score_change_5d=dscore5,
        ))
        replay.append({
            "day": row["day"],
            "close": row.get("close"),
            "sessions_since_exit": since,
            "state": result.state.value,
            "production_ready": result.production_ready,
        })

    counts = {state.value: 0 for state in ReentryState}
    for row in replay:
        counts[row["state"]] = counts.get(row["state"], 0) + 1

    event_windows = []
    day_to_i = {row["day"]: i for i, row in enumerate(rows)}
    sorted_events = [d for d in event_days if d in day_to_i]
    for n, event_day in enumerate(sorted_events):
        start_i = day_to_i[event_day]
        next_i = day_to_i[sorted_events[n + 1]] if n + 1 < len(sorted_events) else len(rows)
        end_i = min(start_i + 61, next_i, len(rows))
        window = replay[start_i:end_i]
        first = {}
        for state in ("CAPITULATION_WATCH", "ACCUMULATION_WATCH", "RECOVERY_WATCH"):
            hit = next((x for x in window if x["state"] == state), None)
            if hit:
                idx = day_to_i[hit["day"]]
                first[state] = {"day": hit["day"], **(_forward_stats(rows, idx) or {})}
            else:
                first[state] = None
        sequence = [x["day"] + ":" + x["state"] for x in window if x["state"] != "INACTIVE"]
        event_windows.append({
            "exit_day": event_day,
            "window_sessions": len(window),
            "first": first,
            "non_inactive_observations": len(sequence),
            "sequence_preview": sequence[:12],
        })

    calibration = []
    for name, trough in CALIBRATION_TROUGHS.items():
        preceding = [e for e in sorted_events if e <= trough]
        event_day = preceding[-1] if preceding else None
        window = next((x for x in event_windows if x["exit_day"] == event_day), None)
        calibration.append({"name": name, "trough": trough, "exit_day": event_day, "window": window})

    crisis_has_reentry_watch = sum(
        1 for x in calibration
        if x["window"] and any(x["window"]["first"].get(s) for s in ("CAPITULATION_WATCH", "ACCUMULATION_WATCH"))
    )
    no_production_promotion = all(not x["production_ready"] for x in replay)
    data_gate = len(rows) >= 1500 and len(sorted_events) >= 10
    status = "GO_FOR_REENTRY_QUALITY_GATE" if data_gate and crisis_has_reentry_watch == 4 and no_production_promotion else "NO_GO"

    out = {
        "release": "R1.1.1 Historical Re-entry Replay",
        "status": status,
        "methodology": {
            "look_ahead_in_features": False,
            "threshold_refit": False,
            "recent_exit_window_sessions": 60,
            "production_ready": False,
            "rule": "Frozen R1.1 research heuristics replayed unchanged after frozen EXIT events.",
        },
        "data": {"daily_rows": len(rows), "frozen_exit_events": len(sorted_events)},
        "state_counts": counts,
        "gates": {
            "data_gate": data_gate,
            "calibration_crises_with_capitulation_or_accumulation_watch": crisis_has_reentry_watch,
            "required_calibration_crises": 4,
            "no_production_promotion": no_production_promotion,
        },
        "calibration_episodes": calibration,
        "event_windows": event_windows,
        "next_gate": "R1.1.2 Re-entry Quality & Premature Entry Gate",
    }
    path = Path("artifacts/reentry_replay.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
