from __future__ import annotations
from typing import Any

CORE_SIGNALS=("market_structure","breadth","volume_distribution","volatility_liquidity","levels_momentum")
CONTEXT_SIGNALS=("rate_ofz","oil_rub","macro_earnings","news_geopolitics")
EXIT_STAGES={"NORMAL","EARLY_WARNING","EXIT_WATCH","CASH_CONFIRMED","DATA_INSUFFICIENT"}
CONTEXT_STATES={"SUPPORTIVE","NEUTRAL","CAUTION","STRESS","DATA_INSUFFICIENT"}
DASHBOARD_RELEASE="R0.5.2 Oil / RUB Live Integration"

def _valid_score(value:Any)->bool: return isinstance(value,(int,float)) and 0<=value<=100

def validate_dashboard_snapshot(snapshot:dict[str,Any])->list[str]:
    errors=[]
    if snapshot.get("release")!=DASHBOARD_RELEASE: errors.append(f"release must be {DASHBOARD_RELEASE}")
    if snapshot.get("source")!="MOEX ISS": errors.append("source must be MOEX ISS")
    if snapshot.get("secid")!="IMOEX": errors.append("secid must be IMOEX")
    if not snapshot.get("as_of"): errors.append("as_of is required")
    if not isinstance(snapshot.get("last_close"),(int,float)): errors.append("last_close must be numeric")
    signals=snapshot.get("signals") or {}
    for key in CORE_SIGNALS:
        item=signals.get(key)
        if not isinstance(item,dict): errors.append(f"core signal {key} is missing"); continue
        if not _valid_score(item.get("score")): errors.append(f"core signal {key}.score must be 0..100")
        if not item.get("quality"): errors.append(f"core signal {key}.quality is required")

    context=snapshot.get("context") or {}; groups=context.get("groups") or {}
    if context.get("state") not in CONTEXT_STATES: errors.append("context.state is invalid")
    if context.get("quality") not in {"LIVE","DELAYED","STALE","ERROR","N/A"}: errors.append("context.quality is invalid")
    cscore=context.get("score"); coverage=context.get("coverage"); available=context.get("available_groups")
    if cscore is not None and not _valid_score(cscore): errors.append("context.score must be null or 0..100")
    if not isinstance(coverage,(int,float)) or not 0<=coverage<=1: errors.append("context.coverage must be 0..1")
    if context.get("total_groups")!=4: errors.append("context.total_groups must equal 4")
    if not isinstance(available,int) or not 0<=available<=4: errors.append("context.available_groups must be 0..4")
    if cscore is None and context.get("state")!="DATA_INSUFFICIENT": errors.append("empty context score requires DATA_INSUFFICIENT state")
    if cscore is not None and (available<2 or coverage<.50): errors.append("aggregate Context requires >=2 groups and >=50% weight coverage")
    for key in CONTEXT_SIGNALS:
        if not isinstance(groups.get(key),dict): errors.append(f"context group {key} is missing")

    rate=groups.get("rate_ofz") or {}; rs=rate.get("score")
    if rs is not None:
        if not _valid_score(rs): errors.append("context group rate_ofz.score must be 0..100")
        if rate.get("quality") not in {"LIVE","DELAYED"}: errors.append("sourced rate_ofz requires LIVE or DELAYED quality")
        if not isinstance(rate.get("key_rate"),(int,float)) or not rate.get("key_rate_day"): errors.append("sourced rate_ofz requires key rate and date")
        cc=rate.get("component_coverage")
        if not isinstance(cc,(int,float)) or not .65<=cc<=1: errors.append("sourced rate_ofz component_coverage must be 0.65..1")
        if not isinstance(rate.get("ofz_count"),int): errors.append("sourced rate_ofz requires ofz_count")
        src=rate.get("sources") or []
        if "Bank of Russia" not in src or not any("MOEX" in str(x) for x in src): errors.append("rate_ofz must disclose official CBR and MOEX sources")
        si=signals.get("rate_ofz") or {}
        if si.get("score")!=rs or si.get("quality")!=rate.get("quality"): errors.append("signals.rate_ofz must match context.groups.rate_ofz")
    elif "rate_ofz" in signals and (signals.get("rate_ofz") or {}).get("score") is not None: errors.append("signals.rate_ofz cannot be populated when context group is N/A")

    oil=groups.get("oil_rub") or {}; os=oil.get("score")
    if os is not None:
        if not _valid_score(os): errors.append("context group oil_rub.score must be 0..100")
        if oil.get("quality") not in {"LIVE","DELAYED"}: errors.append("sourced oil_rub requires LIVE or DELAYED quality")
        cc=oil.get("component_coverage")
        if not isinstance(cc,(int,float)) or not .75<=cc<=1: errors.append("sourced oil_rub component_coverage must be 0.75..1")
        if not oil.get("brent_secid") or not oil.get("latest_day"): errors.append("sourced oil_rub requires Brent contract and latest_day")
        src=oil.get("sources") or []
        if len(src)<2 or not all("MOEX" in str(x) for x in src): errors.append("oil_rub must disclose MOEX Brent and CNYRUB sources")
        si=signals.get("oil_rub") or {}
        if si.get("score")!=os or si.get("quality")!=oil.get("quality"): errors.append("signals.oil_rub must match context.groups.oil_rub")
    elif "oil_rub" in signals and (signals.get("oil_rub") or {}).get("score") is not None: errors.append("signals.oil_rub cannot be populated when context group is N/A")

    for key in ("macro_earnings","news_geopolitics"):
        if (groups.get(key) or {}).get("score") is not None: errors.append(f"context group {key} must remain N/A until live integration")
        if key in signals and (signals.get(key) or {}).get("score") is not None: errors.append(f"signal {key} must remain N/A until live integration")

    crash=snapshot.get("crash") or {}; score=crash.get("score"); weight=crash.get("available_weight"); confirms=crash.get("critical_confirmations")
    if score is not None and not _valid_score(score): errors.append("crash.score must be null or 0..100")
    if not isinstance(weight,(int,float)) or not 0<=weight<=1: errors.append("crash.available_weight must be 0..1")
    if not isinstance(confirms,int) or not 0<=confirms<=4: errors.append("crash.critical_confirmations must be 0..4")
    history=snapshot.get("crash_history")
    if not isinstance(history,list) or not history: errors.append("crash_history is required for R0.5.2 dashboard")
    else:
        for row in history:
            if not isinstance(row,dict) or not row.get("day") or not _valid_score(row.get("score")): errors.append("crash_history rows require day and score 0..100"); break

    gate=snapshot.get("exit_gate") or {}; stage=gate.get("stage")
    if stage not in EXIT_STAGES: errors.append("exit_gate.stage is invalid")
    if not isinstance(gate.get("cash_confirmed"),bool): errors.append("exit_gate.cash_confirmed must be bool")
    if stage=="CASH_CONFIRMED" and gate.get("cash_confirmed") is not True: errors.append("CASH_CONFIRMED stage requires cash_confirmed=true")
    expected={"score_threshold":65.0,"confirmations":3,"persistence":2,"max_5d_return_pct":-3.0,"cooldown_rows":30,"require_breadth_volume":False,"rearm_clear_rows":3}
    params=gate.get("params") or {}
    for key,value in expected.items():
        if params.get(key)!=value: errors.append(f"exit_gate.params.{key} must equal calibrated value {value}")

    bottom=snapshot.get("bottom") or {}
    if bottom.get("score") is not None: errors.append("bottom.score must remain N/A until Bottom Engine data is sourced")
    if bottom.get("state")!="DATA_INSUFFICIENT": errors.append("bottom.state must be DATA_INSUFFICIENT before Re-entry Engine integration")
    calibration=snapshot.get("calibration") or {}
    if calibration.get("release")!="R0.3.3": errors.append("calibration.release must be R0.3.3")
    if calibration.get("false_event_rate")!=.2857: errors.append("calibration.false_event_rate must be 0.2857")
    if calibration.get("detected_episodes")!="4/4": errors.append("calibration.detected_episodes must be 4/4")
    if calibration.get("total_exit_events")!=14 or calibration.get("false_exit_events")!=4: errors.append("calibration event counts are invalid")
    text=str(snapshot).lower()
    if "synthetic" in text or "mock" in text or "demo data" in text: errors.append("live snapshot must not contain synthetic/mock/demo data markers")
    return errors

def assert_dashboard_snapshot(snapshot:dict[str,Any])->None:
    errors=validate_dashboard_snapshot(snapshot)
    if errors: raise ValueError("; ".join(errors))
