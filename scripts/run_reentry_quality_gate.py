from __future__ import annotations

import json
import statistics
from pathlib import Path

INPUT = Path("artifacts/reentry_replay.json")
OUTPUT = Path("artifacts/reentry_quality_gate.json")


def _complete_first(event_windows, state):
    rows = []
    for window in event_windows:
        point = (window.get("first") or {}).get(state)
        if not point:
            continue
        required = (
            point.get("forward_20row_min_return_pct"),
            point.get("forward_20row_end_return_pct"),
        )
        if any(v is None for v in required):
            continue
        rows.append(point)
    return rows


def _summary(rows):
    if not rows:
        return {
            "count": 0,
            "median_forward_20row_min_return_pct": None,
            "worst_forward_20row_min_return_pct": None,
            "median_forward_20row_end_return_pct": None,
            "non_negative_end_share": None,
            "severe_drawdown_le_minus_10_share": None,
            "severe_drawdown_le_minus_15_share": None,
        }
    mins = [float(r["forward_20row_min_return_pct"]) for r in rows]
    ends = [float(r["forward_20row_end_return_pct"]) for r in rows]
    n = len(rows)
    return {
        "count": n,
        "median_forward_20row_min_return_pct": round(statistics.median(mins), 2),
        "worst_forward_20row_min_return_pct": round(min(mins), 2),
        "median_forward_20row_end_return_pct": round(statistics.median(ends), 2),
        "non_negative_end_share": round(sum(x >= 0 for x in ends) / n, 4),
        "severe_drawdown_le_minus_10_share": round(sum(x <= -10 for x in mins) / n, 4),
        "severe_drawdown_le_minus_15_share": round(sum(x <= -15 for x in mins) / n, 4),
    }


def main():
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    windows = source.get("event_windows", [])

    accumulation = _complete_first(windows, "ACCUMULATION_WATCH")
    recovery = _complete_first(windows, "RECOVERY_WATCH")

    accumulation_summary = _summary(accumulation)
    recovery_summary = _summary(recovery)

    # R1.1.2 is a risk-policy gate, not a model-optimization step.
    # No R1.1 thresholds are changed here.
    gates = {
        "source_replay_completed": source.get("status") == "GO_FOR_REENTRY_QUALITY_GATE",
        "accumulation_full_horizon_events_at_least_8": accumulation_summary["count"] >= 8,
        "accumulation_median_drawdown_not_worse_than_minus_8pct": (
            accumulation_summary["median_forward_20row_min_return_pct"] is not None
            and accumulation_summary["median_forward_20row_min_return_pct"] >= -8.0
        ),
        "no_accumulation_event_with_drawdown_worse_than_minus_15pct": (
            accumulation_summary["worst_forward_20row_min_return_pct"] is not None
            and accumulation_summary["worst_forward_20row_min_return_pct"] > -15.0
        ),
        "accumulation_non_negative_20row_end_share_at_least_60pct": (
            accumulation_summary["non_negative_end_share"] is not None
            and accumulation_summary["non_negative_end_share"] >= 0.60
        ),
        "recovery_no_severe_minus_10pct_drawdown": (
            recovery_summary["count"] > 0
            and recovery_summary["worst_forward_20row_min_return_pct"] is not None
            and recovery_summary["worst_forward_20row_min_return_pct"] > -10.0
        ),
        "no_production_promotion": True,
    }

    release_gate_pass = all(gates.values())
    status = "GO_FOR_REENTRY_HOLDOUT" if release_gate_pass else "NO_GO_PREMATURE_REENTRY_RISK"

    payload = {
        "release": "R1.1.2 Re-entry Quality & Premature Entry Gate",
        "status": status,
        "methodology": {
            "threshold_refit": False,
            "production_ready": False,
            "purpose": "Reject re-entry logic that exposes capital to materially premature accumulation signals.",
            "note": "Gate thresholds are conservative capital-risk policy limits; they do not alter R1.1 signal thresholds.",
        },
        "accumulation_watch": accumulation_summary,
        "recovery_watch": recovery_summary,
        "gates": gates,
        "release_gate_pass": release_gate_pass,
        "decision": (
            "Proceed to holdout validation without promoting to production."
            if release_gate_pass
            else "Do not promote Re-entry Radar. Preserve as research; redesign signal logic before any holdout or action mapping."
        ),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
