from __future__ import annotations

from typing import Any

CORE_SIGNALS = (
    "market_structure",
    "breadth",
    "volume_distribution",
    "volatility_liquidity",
    "levels_momentum",
)
OPTIONAL_SIGNALS = (
    "rate_ofz",
    "oil_rub",
    "macro_earnings",
    "news_geopolitics",
)
EXIT_STAGES = {"NORMAL", "EARLY_WARNING", "EXIT_WATCH", "CASH_CONFIRMED", "DATA_INSUFFICIENT"}
CONTEXT_STATES = {"SUPPORTIVE", "NEUTRAL", "CAUTION", "STRESS", "DATA_INSUFFICIENT"}
DASHBOARD_RELEASE = "R0.5.0 Context Layer Foundation"


def validate_dashboard_snapshot(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if snapshot.get("release") != DASHBOARD_RELEASE:
        errors.append(f"release must be {DASHBOARD_RELEASE}")
    if snapshot.get("source") != "MOEX ISS":
        errors.append("source must be MOEX ISS")
    if snapshot.get("secid") != "IMOEX":
        errors.append("secid must be IMOEX")
    if not snapshot.get("as_of"):
        errors.append("as_of is required")
    if not isinstance(snapshot.get("last_close"), (int, float)):
        errors.append("last_close must be numeric")

    signals = snapshot.get("signals") or {}
    for key in CORE_SIGNALS:
        item = signals.get(key)
        if not isinstance(item, dict):
            errors.append(f"core signal {key} is missing")
            continue
        score = item.get("score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            errors.append(f"core signal {key}.score must be 0..100")
        if not item.get("quality"):
            errors.append(f"core signal {key}.quality is required")

    for key in OPTIONAL_SIGNALS:
        if key in signals:
            item = signals[key]
            if item not in (None, {}) and isinstance(item, dict) and item.get("score") is not None:
                errors.append(f"optional signal {key} must remain N/A until sourced")

    context = snapshot.get("context") or {}
    if context.get("state") not in CONTEXT_STATES:
        errors.append("context.state is invalid")
    if context.get("quality") not in {"LIVE", "DELAYED", "STALE", "ERROR", "N/A"}:
        errors.append("context.quality is invalid")
    cscore = context.get("score")
    if cscore is not None and (not isinstance(cscore, (int, float)) or not 0 <= cscore <= 100):
        errors.append("context.score must be null or 0..100")
    coverage = context.get("coverage")
    if not isinstance(coverage, (int, float)) or not 0 <= coverage <= 1:
        errors.append("context.coverage must be 0..1")
    if context.get("total_groups") != 4:
        errors.append("context.total_groups must equal 4")
    available_groups = context.get("available_groups")
    if not isinstance(available_groups, int) or not 0 <= available_groups <= 4:
        errors.append("context.available_groups must be 0..4")
    if cscore is None and context.get("state") != "DATA_INSUFFICIENT":
        errors.append("empty context score requires DATA_INSUFFICIENT state")
    groups = context.get("groups") or {}
    for key in OPTIONAL_SIGNALS:
        item = groups.get(key)
        if not isinstance(item, dict):
            errors.append(f"context group {key} is missing")
            continue
        if item.get("score") is not None:
            errors.append(f"context group {key} must remain N/A until live source integration")

    crash = snapshot.get("crash") or {}
    score = crash.get("score")
    if score is not None and (not isinstance(score, (int, float)) or not 0 <= score <= 100):
        errors.append("crash.score must be null or 0..100")
    weight = crash.get("available_weight")
    if not isinstance(weight, (int, float)) or not 0 <= weight <= 1:
        errors.append("crash.available_weight must be 0..1")
    confirms = crash.get("critical_confirmations")
    if not isinstance(confirms, int) or not 0 <= confirms <= 4:
        errors.append("crash.critical_confirmations must be 0..4")

    history = snapshot.get("crash_history")
    if not isinstance(history, list) or not history:
        errors.append("crash_history is required for R0.5.0 dashboard")
    else:
        for row in history:
            if not isinstance(row, dict) or not row.get("day"):
                errors.append("crash_history rows require day")
                break
            hscore = row.get("score")
            if not isinstance(hscore, (int, float)) or not 0 <= hscore <= 100:
                errors.append("crash_history score must be 0..100")
                break

    gate = snapshot.get("exit_gate") or {}
    stage = gate.get("stage")
    if stage not in EXIT_STAGES:
        errors.append("exit_gate.stage is invalid")
    if not isinstance(gate.get("cash_confirmed"), bool):
        errors.append("exit_gate.cash_confirmed must be bool")
    if stage == "CASH_CONFIRMED" and gate.get("cash_confirmed") is not True:
        errors.append("CASH_CONFIRMED stage requires cash_confirmed=true")

    params = gate.get("params") or {}
    expected = {
        "score_threshold": 65.0,
        "confirmations": 3,
        "persistence": 2,
        "max_5d_return_pct": -3.0,
        "cooldown_rows": 30,
        "require_breadth_volume": False,
        "rearm_clear_rows": 3,
    }
    for key, value in expected.items():
        if params.get(key) != value:
            errors.append(f"exit_gate.params.{key} must equal calibrated value {value}")

    bottom = snapshot.get("bottom") or {}
    if bottom.get("score") is not None:
        errors.append("bottom.score must remain N/A until Bottom Engine data is sourced")
    if bottom.get("state") != "DATA_INSUFFICIENT":
        errors.append("bottom.state must be DATA_INSUFFICIENT before Re-entry Engine integration")

    calibration = snapshot.get("calibration") or {}
    if calibration.get("release") != "R0.3.3":
        errors.append("calibration.release must be R0.3.3")
    if calibration.get("false_event_rate") != 0.2857:
        errors.append("calibration.false_event_rate must be 0.2857")
    if calibration.get("detected_episodes") != "4/4":
        errors.append("calibration.detected_episodes must be 4/4")
    if calibration.get("total_exit_events") != 14:
        errors.append("calibration.total_exit_events must be 14")
    if calibration.get("false_exit_events") != 4:
        errors.append("calibration.false_exit_events must be 4")

    text = str(snapshot).lower()
    if "synthetic" in text or "mock" in text or "demo data" in text:
        errors.append("live snapshot must not contain synthetic/mock/demo data markers")

    return errors


def assert_dashboard_snapshot(snapshot: dict[str, Any]) -> None:
    errors = validate_dashboard_snapshot(snapshot)
    if errors:
        raise ValueError("; ".join(errors))
