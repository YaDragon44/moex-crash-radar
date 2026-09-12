from __future__ import annotations

import json
from pathlib import Path

from moex_crash_radar.regime import MarketRegime, RegimeInputs, classify_regime

PERSISTENCE = 2


def _ret5(rows: list[dict], i: int) -> float | None:
    if i < 5:
        return None
    base = float(rows[i - 5]["close"])
    if base <= 0:
        return None
    return round((float(rows[i]["close"]) / base - 1.0) * 100.0, 2)


def _stage(day: str, score: float, confirmations: int, event_days: set[str]) -> str:
    if day in event_days:
        return "EXIT_CONFIRMED"
    if score >= 65 and confirmations >= 2:
        return "EXIT_WATCH"
    if score >= 56:
        return "EARLY_WARNING"
    return "NORMAL"


def _stable_regimes(raw: list[str], event_flags: list[bool]) -> list[str]:
    if not raw:
        return []
    stable = [raw[0]]
    candidate = None
    run = 0
    for i in range(1, len(raw)):
        current = stable[-1]
        target = raw[i]
        # A validated frozen EXIT event is never suppressed by smoothing.
        if event_flags[i] and target == MarketRegime.RISK_OFF.value:
            stable.append(target)
            candidate = None
            run = 0
            continue
        if target == current:
            stable.append(current)
            candidate = None
            run = 0
            continue
        if target == candidate:
            run += 1
        else:
            candidate = target
            run = 1
        if run >= PERSISTENCE:
            stable.append(target)
            candidate = None
            run = 0
        else:
            stable.append(current)
    return stable


def _transition_count(states: list[str]) -> int:
    return sum(1 for a, b in zip(states, states[1:]) if a != b)


def main() -> None:
    source = json.loads(Path("artifacts/historical_evidence.json").read_text(encoding="utf-8"))
    rows = source.get("daily_evidence") or []
    event_days = set(source.get("frozen_exit_validation", {}).get("event_days") or [])
    if not rows:
        raise SystemExit("daily_evidence missing; run updated historical evidence first")

    raw_states: list[str] = []
    event_flags: list[bool] = []
    details: list[dict] = []
    for i, row in enumerate(rows):
        score = row.get("score")
        conf = row.get("critical_confirmations")
        if score is None or conf is None:
            regime = MarketRegime.DATA_INSUFFICIENT.value
            transition = "N/A"
            stage = "DATA_INSUFFICIENT"
        else:
            score = float(score)
            conf = int(conf)
            stage = _stage(row["day"], score, conf, event_days)
            result = classify_regime(RegimeInputs(score, stage, conf, _ret5(rows, i)))
            regime = result.regime.value
            transition = result.transition
        raw_states.append(regime)
        event_flags.append(row["day"] in event_days)
        details.append({"day": row["day"], "raw_regime": regime, "transition": transition, "exit_stage": stage})

    stable_states = _stable_regimes(raw_states, event_flags)
    for item, stable in zip(details, stable_states):
        item["stable_regime"] = stable

    raw_transitions = _transition_count(raw_states)
    stable_transitions = _transition_count(stable_states)
    reduction = 1.0 - (stable_transitions / raw_transitions) if raw_transitions else 0.0
    event_preserved = all(
        stable_states[i] == MarketRegime.RISK_OFF.value
        for i, flag in enumerate(event_flags)
        if flag
    )
    unvalidated_reentry_absent = all(
        s not in {MarketRegime.CAPITULATION.value, MarketRegime.ACCUMULATION.value, MarketRegime.RECOVERY.value}
        for s in stable_states
    )
    gate_pass = bool(event_preserved and unvalidated_reentry_absent and reduction >= 0.30)

    counts: dict[str, int] = {}
    for state in stable_states:
        counts[state] = counts.get(state, 0) + 1

    payload = {
        "release": "R1.0.2 Full Daily Regime Stability Replay",
        "status": "GO_FOR_TRANSITION_VALIDATION" if gate_pass else "NO_GO",
        "methodology": {
            "look_ahead": False,
            "threshold_refit": False,
            "persistence_sessions": PERSISTENCE,
            "validated_exit_override": True,
            "crowd_drives_regime": False,
            "vulnerability_drives_regime": False,
            "reentry_enabled": False,
        },
        "data": {"daily_rows": len(rows), "frozen_exit_events": len(event_days)},
        "stability": {
            "raw_transition_count": raw_transitions,
            "stable_transition_count": stable_transitions,
            "transition_reduction": round(reduction, 4),
            "gate_min_reduction": 0.30,
            "event_preserved": event_preserved,
            "no_unvalidated_reentry": unvalidated_reentry_absent,
            "gate_pass": gate_pass,
            "stable_state_counts": counts,
        },
        "daily": details,
    }
    out = Path("artifacts/regime_daily_replay.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "daily"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
