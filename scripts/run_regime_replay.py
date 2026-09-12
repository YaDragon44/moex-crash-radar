from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from moex_crash_radar.regime import RegimeInputs, classify_regime

EPISODES = (
    ("COVID_2020", "2020-03-18"),
    ("FEB_2022", "2022-02-24"),
    ("SEP_2022", "2022-10-10"),
    ("CORRECTION_2024", "2024-09-03"),
)


def _exit_stage(score: float, confirmations: int) -> str:
    # Historical replay intentionally does not reconstruct sticky CASH_CONFIRMED.
    # It uses only same-day frozen thresholds, so no future event history leaks in.
    if score >= 65 and confirmations >= 3:
        return "EXIT_WATCH"
    if score >= 56:
        return "EARLY_WARNING"
    return "NORMAL"


def main() -> None:
    src = Path("artifacts/historical_evidence.json")
    payload = json.loads(src.read_text(encoding="utf-8"))
    diagnostics = payload["frozen_exit_validation"]["event_diagnostics"]
    event_days = {row["day"] for row in diagnostics}

    # The historical evidence artifact does not expose every daily row. Therefore
    # R1.0.1 first validates regime semantics at all frozen EXIT events and named
    # crisis episodes. A full daily state-machine replay is deferred until daily
    # evidence is exported explicitly; we do not invent missing rows.
    event_results = []
    for row in diagnostics:
        score = float(row["score"])
        conf = int(row["critical_confirmations"])
        stage = "EXIT_WATCH" if row["day"] in event_days else _exit_stage(score, conf)
        result = classify_regime(RegimeInputs(score, stage, conf, None))
        event_results.append({
            "day": row["day"],
            "false_event": row["false_event"],
            "regime": result.regime.value,
            "transition": result.transition,
        })

    episode_rows = []
    detection = payload["frozen_exit_validation"]["episode_detection"]
    by_name = {x["name"]: x for x in detection}
    for name, trough in EPISODES:
        row = by_name.get(name, {})
        first = row.get("first_frozen_exit")
        lead = (date.fromisoformat(trough) - date.fromisoformat(first)).days if first else None
        episode_rows.append({"name": name, "trough": trough, "first_frozen_exit": first, "lead_days": lead})

    all_detected = all(x["first_frozen_exit"] is not None for x in episode_rows)
    no_reentry_claims = all(x["regime"] not in {"CAPITULATION", "ACCUMULATION", "RECOVERY"} for x in event_results)
    payload_out = {
        "release": "R1.0.1 Historical Regime Replay",
        "status": "GO_FOR_DAILY_REPLAY" if all_detected and no_reentry_claims else "NO_GO",
        "methodology": {
            "look_ahead": False,
            "threshold_refit": False,
            "crowd_drives_regime": False,
            "vulnerability_drives_regime": False,
            "reentry_enabled": False,
            "scope": "event-level semantic replay; full daily stability replay requires explicit daily evidence export",
        },
        "gates": {
            "all_four_calibration_crises_have_frozen_exit": all_detected,
            "no_unvalidated_reentry_regimes": no_reentry_claims,
        },
        "episodes": episode_rows,
        "event_results": event_results,
    }
    out = Path("artifacts/regime_replay.json")
    out.write_text(json.dumps(payload_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload_out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
