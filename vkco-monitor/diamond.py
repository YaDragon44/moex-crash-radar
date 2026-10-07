from __future__ import annotations
from typing import Any

def build(fundamental: dict[str, Any], valuation: dict[str, Any], trade: dict[str, Any],
          strategy2: dict[str, Any], strategy4: dict[str, Any]) -> dict[str, Any]:
    """Read-only Diamond classifier. Never opens/closes positions or sizes leverage."""
    if fundamental.get("status") != "OK" or valuation.get("status") != "OK":
        return {"status":"DATA_UNAVAILABLE","read_only":True,"reason":"FUNDAMENTAL_OR_VALUATION_UNAVAILABLE"}

    indicators=fundamental.get("indicators") or []
    green=sum(1 for x in indicators if x.get("light")=="GREEN")
    fundamental_ok=len(indicators)>=4 and green>=4
    mos=float(valuation.get("margin_of_safety_pct") or 0)
    valuation_ok=mos>=20.0

    s1_confirmed=trade.get("status") in {"READY","OPEN","TP1","TP2","TRAILING"}
    s2_confirmed=strategy2.get("signal")=="BUY" or bool(strategy2.get("position"))
    s4_confirmed=strategy4.get("decision")=="READY" or bool(strategy4.get("position"))
    technical_confirmations=sum((s1_confirmed,s2_confirmed,s4_confirmed))

    if fundamental_ok and valuation_ok and technical_confirmations>=1:
        state="DIAMOND_CONFIRMED"
    elif fundamental_ok and valuation_ok:
        state="DIAMOND_CANDIDATE"
    else:
        state="NO_DIAMOND"

    return {
        "status":"OK","state":state,"read_only":True,
        "fundamental_ok":fundamental_ok,"fundamental_green":green,
        "valuation_ok":valuation_ok,"margin_of_safety_pct":round(mos,1),
        "technical_confirmations":technical_confirmations,
        "technical":{"s1":s1_confirmed,"s2":s2_confirmed,"s4":s4_confirmed},
        "position_framework":{
            "CORE":"Investment thesis; do not manage with S1 trade TP/stop.",
            "TRADE":"Technical sleeve; manage only by the selected strategy rules.",
            "FUTURES":"Optional tactical leverage only after a separate futures contract/liquidity/GO/risk check; never inferred from the equity signal."
        },
        "note":"Classification only. No broker order, no automatic Telegram, no strategy feedback."
    }
