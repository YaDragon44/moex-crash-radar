from __future__ import annotations

import json
import sys
from pathlib import Path

SNAPSHOT = Path("data/crypto-radar/snapshot.json")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def market_stress(total24):
    if total24 is None: return None
    if total24 >= 2: return 15
    if total24 >= 0: return 25
    if total24 > -2: return 40
    if total24 > -4: return 55
    if total24 > -7: return 75
    return 90


def leverage_risk(price24, oi24):
    if price24 is None or oi24 is None: return None
    if price24 > 0 and oi24 > 0:
        return 80 if oi24 >= 8 else 70 if oi24 >= 4 else 55
    if price24 < 0 and oi24 > 0:
        return 90 if oi24 >= 8 else 80 if oi24 >= 4 else 65
    if price24 < 0 and oi24 < 0:
        return 55 if price24 <= -2 else 45
    if price24 > 0 and oi24 < 0:
        return 30
    return 40


def funding_risk(funding_pct):
    if funding_pct is None: return None
    a = abs(funding_pct)
    if a < .01: return 20
    if a < .03: return 45
    if a < .06: return 70
    return 90


def positioning_risk(lsr):
    if lsr is None or lsr <= 0: return None
    if .90 <= lsr <= 1.10: return 20
    if .75 <= lsr < .90 or 1.10 < lsr <= 1.30: return 40
    if .60 <= lsr < .75 or 1.30 < lsr <= 1.50: return 65
    return 85


def liquidity_risk(stable_delta):
    if stable_delta is None: return None
    if stable_delta >= .20: return 20
    if stable_delta >= 0: return 35
    if stable_delta > -.20: return 55
    return 75


def risk_label(score):
    if score is None: return "N/A"
    if score < 30: return "LOW"
    if score < 45: return "MODERATE"
    if score < 60: return "ELEVATED"
    if score < 75: return "HIGH"
    return "CRITICAL"


def build_risk(s):
    m = s.get("market") or {}
    d = s.get("derivatives") or {}
    c = s.get("context") or {}
    components = {
        "market_stress": market_stress(num(m.get("total_change_24h_pct"))),
        "leverage": leverage_risk(num(d.get("price_change_24h_pct")), num(d.get("oi_change_24h_pct"))),
        "funding_extreme": funding_risk(num(d.get("funding_pct"))),
        "positioning_extreme": positioning_risk(num(d.get("long_short_ratio"))),
        "liquidity_context": liquidity_risk(num(c.get("stablecoin_market_cap_change_24h_pct"))),
    }
    weights = {
        "market_stress": .30,
        "leverage": .30,
        "funding_extreme": .15,
        "positioning_extreme": .15,
        "liquidity_context": .10,
    }
    present = [k for k, v in components.items() if v is not None]
    coverage = sum(weights[k] for k in present) * 100
    score = None
    if coverage >= 80:
        sw = sum(weights[k] for k in present)
        score = round(sum(weights[k] * components[k] for k in present) / sw)
    return {
        "model": "risk-v1-provisional",
        "provisional": True,
        "coverage_pct": round(coverage),
        "score": score,
        "status": risk_label(score),
        "components": components,
        "reason": "Provisional composite; historical calibration required",
    }


def candidate_regime(s, risk):
    m = s.get("market") or {}
    crowd = s.get("crowd") or {}
    total24 = num(m.get("total_change_24h_pct"))
    rs = risk.get("status")
    cs = crowd.get("state")
    if rs == "CRITICAL" and total24 is not None and total24 <= -5:
        return "PANIC"
    if rs in {"HIGH", "CRITICAL"} and total24 is not None and total24 < -2:
        return "RISK-OFF"
    if cs in {"GREED", "EUPHORIA"} and rs in {"ELEVATED", "HIGH", "CRITICAL"} and total24 is not None and total24 <= 0:
        return "DISTRIBUTION"
    if total24 is not None and total24 > 1 and rs in {"LOW", "MODERATE"}:
        return "RISK-ON"
    if total24 is not None and total24 > 1 and rs in {"ELEVATED", "HIGH"}:
        return "RISK-ON / OVERHEATED"
    if total24 is not None and total24 < -2 and rs == "ELEVATED":
        return "RISK-OFF"
    return "NEUTRAL"


def build_regime(candidate, previous):
    prev = (previous or {}).get("regime") or {}
    prev_candidate = prev.get("candidate")
    prev_count = int(prev.get("candidate_count") or 0)
    prev_status = prev.get("status")
    prev_confirmed = bool(prev.get("confirmed"))
    count = prev_count + 1 if candidate == prev_candidate else 1

    if count >= 2:
        transition = "STABLE"
        if prev_confirmed and prev_status and prev_status != candidate:
            transition = f"{prev_status} -> {candidate}"
        elif not prev_confirmed:
            transition = f"CONFIRMED -> {candidate}"
        return {
            "model": "regime-v1-provisional",
            "provisional": True,
            "status": candidate,
            "candidate": candidate,
            "candidate_count": count,
            "confirmed": True,
            "transition": transition,
            "confirmation_rule": "2 consecutive observations",
        }

    status = prev_status if prev_confirmed and prev_status else candidate
    transition = f"WATCH {candidate} · 1/2"
    if prev_confirmed and prev_status and prev_status != candidate:
        transition = f"WATCH {prev_status} -> {candidate} · 1/2"
    return {
        "model": "regime-v1-provisional",
        "provisional": True,
        "status": status,
        "candidate": candidate,
        "candidate_count": count,
        "confirmed": False,
        "transition": transition,
        "confirmation_rule": "2 consecutive observations",
    }


def actions(s, risk, regime):
    crowd = s.get("crowd") or {}
    if not crowd.get("quality_passed") or risk.get("score") is None:
        return {"investor": "WAIT", "trader": "WAIT", "why": ["Quality Gate blocked", "Risk unavailable", "No strong action"], "provisional": True}

    rs, rg, cs = risk["status"], regime["status"], crowd.get("state")
    if rg == "PANIC" or rs == "CRITICAL":
        investor, trader = "RAISE CASH", "HEDGE"
    elif rg in {"RISK-OFF", "DISTRIBUTION"} or rs == "HIGH":
        investor, trader = "REDUCE RISK", "REDUCE EXPOSURE"
    elif rs == "ELEVATED":
        investor = "DO NOT CHASE" if cs in {"GREED", "EUPHORIA"} else "HOLD"
        trader = "WAIT" if rg == "NEUTRAL" else "SELECTIVE LONG"
    elif rg == "RISK-ON" and rs in {"LOW", "MODERATE"}:
        investor, trader = "BUY GRADUALLY", "LONG BIAS"
    elif rg == "RISK-ON / OVERHEATED":
        investor, trader = "DO NOT CHASE", "SELECTIVE LONG"
    else:
        investor, trader = "HOLD", "WAIT"

    labels = {
        "market_stress": "Market stress",
        "leverage": "Price/OI leverage",
        "funding_extreme": "Funding extremity",
        "positioning_extreme": "Long/Short extremity",
        "liquidity_context": "Stablecoin liquidity",
    }
    ranked = sorted(((k, v) for k, v in risk["components"].items() if v is not None), key=lambda x: x[1], reverse=True)[:3]
    why = [f"{labels[k]} {v}/100" for k, v in ranked]
    return {"investor": investor, "trader": trader, "why": why, "provisional": True}


def main():
    previous = None
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.exists():
            try:
                previous = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                previous = None

    s = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    crowd = s.get("crowd") or {}
    if not crowd.get("quality_passed"):
        s["risk"] = {"model": "risk-v1-provisional", "provisional": True, "coverage_pct": 0, "score": None, "status": "N/A", "components": {}, "reason": "Crowd Quality Gate blocked"}
        s["regime"] = {"model": "regime-v1-provisional", "provisional": True, "status": "N/A", "candidate": "N/A", "candidate_count": 0, "confirmed": False, "transition": "NO DATA", "confirmation_rule": "2 consecutive observations"}
        s["transition"] = {"status": "NO DATA", "confirmed": False}
        s["action_engine"] = {"investor": "WAIT", "trader": "WAIT", "why": ["Quality Gate blocked", "Risk unavailable", "No strong action"], "provisional": True}
    else:
        risk = build_risk(s)
        regime = build_regime(candidate_regime(s, risk), previous)
        s["risk"] = risk
        s["regime"] = regime
        s["transition"] = {"status": regime["transition"], "confirmed": regime["confirmed"]}
        s["action_engine"] = actions(s, risk, regime)

    s["version"] = "1.5"
    SNAPSHOT.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"version": s["version"], "risk": s["risk"].get("status"), "risk_score": s["risk"].get("score"), "regime": s["regime"].get("status"), "transition": s["transition"].get("status"), "investor": s["action_engine"].get("investor"), "trader": s["action_engine"].get("trader")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
