from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from moex_crash_radar.crowd_transition import stable_states

HIST = Path("artifacts/historical_evidence.json")
BLIND = Path("artifacts/blind_crash_replay.json")
CROWD = Path("artifacts/crowd_replay.json")
OUT = Path("artifacts/crowd_incremental_value.json")
CAL_END = "2024-09-30"
HOLDOUT_START = "2024-10-01"
RECENT_WINDOW = 10


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing prerequisite artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_pass(name: str, *, state: str, recent_falling_fast: bool) -> bool:
    fear = state in ("FEAR", "PANIC")
    if name == "STABLE_FEAR":
        return fear
    if name == "RECENT_FALLING_FAST":
        return recent_falling_fast
    if name == "FEAR_OR_FALLING_FAST":
        return fear or recent_falling_fast
    raise ValueError(name)


def annotate(events: list[dict], stable, by_day: dict[str, int]) -> list[dict]:
    out = []
    for event in events:
        day = event.get("day")
        if not day or day not in by_day:
            out.append({**event, "crowd_status": "N/A"})
            continue
        i = by_day[day]
        row = stable[i]
        lo = max(0, i - RECENT_WINDOW + 1)
        recent_ff = any(r.falling_fast for r in stable[lo : i + 1])
        out.append({
            **event,
            "crowd_status": "OK",
            "stable_crowd_state": row.stable_state,
            "crowd_score": row.score,
            "crowd_delta_5": row.delta_5,
            "recent_falling_fast_10sessions": recent_ff,
        })
    return out


def eval_candidate(events: list[dict], name: str, truth_key: str) -> dict:
    usable = [e for e in events if e.get("crowd_status") == "OK" and truth_key in e]
    true_events = [e for e in usable if bool(e[truth_key])]
    false_events = [e for e in usable if not bool(e[truth_key])]
    kept_true = [e for e in true_events if candidate_pass(name, state=e["stable_crowd_state"], recent_falling_fast=e["recent_falling_fast_10sessions"])]
    kept_false = [e for e in false_events if candidate_pass(name, state=e["stable_crowd_state"], recent_falling_fast=e["recent_falling_fast_10sessions"])]
    return {
        "rule": name,
        "true_events": len(true_events),
        "true_events_kept": len(kept_true),
        "true_recall": round(len(kept_true) / len(true_events), 4) if true_events else None,
        "false_events": len(false_events),
        "false_events_kept": len(kept_false),
        "false_events_removed": len(false_events) - len(kept_false),
        "admissible": bool(true_events) and len(kept_true) == len(true_events) and (len(false_events) - len(kept_false)) >= 1,
    }


def main() -> None:
    hist = load(HIST)
    blind = load(BLIND)
    crowd = load(CROWD)

    raw_rows = [SimpleNamespace(**r) for r in crowd.get("rows", [])]
    stable = stable_states(raw_rows, persistence=3, hysteresis=5.0)
    by_day = {r.day: i for i, r in enumerate(stable)}

    cal_events = []
    for e in hist.get("frozen_exit_validation", {}).get("event_diagnostics", []):
        if e.get("day", "") <= CAL_END:
            cal_events.append({
                "day": e.get("day"),
                "true_crash_event": not bool(e.get("false_event")),
                "forward_20row_min_drawdown_pct": e.get("forward_20row_min_drawdown_pct"),
            })

    holdout_events = []
    for e in blind.get("blind_results", {}).get("event_diagnostics", []):
        if e.get("status") == "INCOMPLETE_FORWARD_HORIZON":
            continue
        if e.get("day", "") >= HOLDOUT_START:
            holdout_events.append({
                "day": e.get("day"),
                "true_crash_event": bool(e.get("true_crash_event")),
                "forward_20row_min_drawdown_pct": e.get("forward_20row_min_drawdown_pct"),
            })

    cal = annotate(cal_events, stable, by_day)
    hold = annotate(holdout_events, stable, by_day)
    names = ["STABLE_FEAR", "RECENT_FALLING_FAST", "FEAR_OR_FALLING_FAST"]
    calibration_results = [eval_candidate(cal, name, "true_crash_event") for name in names]

    selected = next((r["rule"] for r in calibration_results if r["admissible"]), None)
    holdout_result = eval_candidate(hold, selected, "true_crash_event") if selected else None

    incremental = bool(
        selected
        and holdout_result
        and holdout_result.get("true_recall") == 1.0
        and holdout_result.get("false_events_removed", 0) >= 1
    )

    payload = {
        "release": "R0.8.3 Crowd Incremental Value Test",
        "status": "INCREMENTAL_VALUE" if incremental else "NO_INCREMENTAL_VALUE",
        "methodology": {
            "look_ahead": False,
            "calibration_end": CAL_END,
            "holdout_start": HOLDOUT_START,
            "recent_falling_fast_window_sessions": RECENT_WINDOW,
            "candidate_rules_frozen_before_holdout": names,
            "selection_rule": "Calibration candidate must preserve 100% true crash events and remove >=1 false EXIT event; selected rule must preserve 100% holdout true events and remove >=1 holdout false event.",
            "threshold_refit": False,
            "frozen_crash_exit_changed": False,
            "production_weight": False,
        },
        "data_quality": {
            "crowd_rows": len(raw_rows),
            "calibration_exit_events": len(cal),
            "holdout_exit_events_complete": len(hold),
            "calibration_events_with_crowd": sum(1 for e in cal if e.get("crowd_status") == "OK"),
            "holdout_events_with_crowd": sum(1 for e in hold if e.get("crowd_status") == "OK"),
        },
        "calibration_results": calibration_results,
        "selected_candidate": selected,
        "holdout_result": holdout_result,
        "calibration_event_diagnostics": cal,
        "holdout_event_diagnostics": hold,
        "decision": "Crowd may be considered for production integration only if incremental value survives the frozen holdout rule. Otherwise keep Crowd as research/context and do not alter EXIT.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
