from __future__ import annotations

import json
import statistics
from pathlib import Path

from moex_crash_radar.reentry_v2 import ReentryV2Inputs, ReentryV2State, classify_reentry_v2

INPUT = Path("artifacts/historical_evidence.json")
OUTPUT = Path("artifacts/reentry_v2_replay.json")


def pct(a: float, b: float) -> float:
    return (b / a - 1.0) * 100.0


def forward(rows, i, horizon=20):
    if i + horizon >= len(rows):
        return None
    p = float(rows[i]["close"])
    f = [float(r["close"]) for r in rows[i:i+horizon+1]]
    return {
        "min": round(pct(p, min(f)), 2),
        "end": round(pct(p, f[-1]), 2),
    }


def main():
    src = json.loads(INPUT.read_text(encoding="utf-8"))
    rows = src.get("daily_evidence") or []
    event_days = src.get("frozen_exit_validation", {}).get("event_days") or []
    events = set(event_days)
    if len(rows) < 1500 or not events:
        raise SystemExit("R1.1.3 requires PIT daily evidence and frozen EXIT events")

    last_exit = None
    replay = []
    for i, row in enumerate(rows):
        if row["day"] in events:
            last_exit = i
        since = None if last_exit is None else i - last_exit

        def ret(n):
            if i < n or row.get("close") is None or rows[i-n].get("close") is None:
                return None
            return pct(float(rows[i-n]["close"]), float(row["close"]))

        def ds(n):
            if i < n or row.get("score") is None or rows[i-n].get("score") is None:
                return None
            return float(row["score"]) - float(rows[i-n]["score"])

        result = classify_reentry_v2(ReentryV2Inputs(
            sessions_since_exit=since,
            crash_score=row.get("score"),
            critical_confirmations=row.get("critical_confirmations"),
            return_5d_pct=ret(5),
            return_10d_pct=ret(10),
            crash_score_change_5d=ds(5),
            crash_score_change_10d=ds(10),
        ))
        replay.append({"day": row["day"], "state": result.state.value})

    day_i = {r["day"]: i for i, r in enumerate(rows)}
    sorted_events = [d for d in event_days if d in day_i]
    first_acc = []
    first_rec = []
    windows = []
    for n, event in enumerate(sorted_events):
        a = day_i[event]
        b = min(a + 61, day_i[sorted_events[n+1]] if n+1 < len(sorted_events) else len(rows), len(rows))
        first = {}
        for state in ("CAPITULATION_WATCH", "STABILIZATION_WATCH", "ACCUMULATION_WATCH", "RECOVERY_WATCH"):
            hit_i = next((j for j in range(a, b) if replay[j]["state"] == state), None)
            point = None if hit_i is None else {"day": rows[hit_i]["day"], **(forward(rows, hit_i) or {})}
            first[state] = point
            if point and "min" in point:
                if state == "ACCUMULATION_WATCH": first_acc.append(point)
                if state == "RECOVERY_WATCH": first_rec.append(point)
        windows.append({"exit_day": event, "first": first})

    def summary(points):
        if not points:
            return {"count": 0, "median_min": None, "worst_min": None, "median_end": None, "non_negative_end_share": None}
        mins = [p["min"] for p in points]
        ends = [p["end"] for p in points]
        return {
            "count": len(points),
            "median_min": round(statistics.median(mins), 2),
            "worst_min": round(min(mins), 2),
            "median_end": round(statistics.median(ends), 2),
            "non_negative_end_share": round(sum(x >= 0 for x in ends) / len(ends), 4),
        }

    acc = summary(first_acc)
    rec = summary(first_rec)
    # Predeclared comparison gate: improvement must be material and must remove
    # the catastrophic premature-entry failure seen in R1.1.2.
    gates = {
        "accumulation_complete_events_at_least_6": acc["count"] >= 6,
        "accumulation_worst_drawdown_better_than_minus_15": acc["worst_min"] is not None and acc["worst_min"] > -15.0,
        "accumulation_non_negative_end_share_at_least_60pct": acc["non_negative_end_share"] is not None and acc["non_negative_end_share"] >= .60,
        "no_production_promotion": True,
    }
    out = {
        "release": "R1.1.3 Re-entry Logic Redesign Replay",
        "status": "GO_FOR_HOLDOUT" if all(gates.values()) else "NO_GO_REDESIGN",
        "methodology": {
            "threshold_refit_after_result": False,
            "production_ready": False,
            "new_external_indicators": False,
            "design_change": "Require 10-session stabilization before accumulation; separate stabilization from accumulation.",
        },
        "accumulation": acc,
        "recovery": rec,
        "gates": gates,
        "event_windows": windows,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
