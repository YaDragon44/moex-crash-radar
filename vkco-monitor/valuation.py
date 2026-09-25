from __future__ import annotations
from typing import Any

# Transparent scenario assumptions, not market-consensus targets.
# Scenario multiples remain explicit assumptions until comparable-company evidence is available.\nSCENARIOS=(("BEAR",4.0),("BASE",6.0),("BULL",8.0))

def build(price:float, fundamentals:dict[str,Any], analysis:dict[str,Any])->dict[str,Any]:
    try:
        shares=float(fundamentals["issue_size"])
        f=analysis["facts"]; net_debt=float(f["net_debt_bln"])*1e9
        ebitda=float(f["guidance_ebitda_2026_bln"])*1e9
        if min(price,shares,ebitda)<=0: raise ValueError("invalid inputs")
    except Exception as exc:
        return {"status":"DATA_UNAVAILABLE","error":type(exc).__name__,"read_only":True}
    market_cap=price*shares;ev=market_cap+net_debt
    ev_ebitda=ev/ebitda
    scenarios=[]
    for name,multiple in SCENARIOS:
        equity=max(multiple*ebitda-net_debt,0.0)
        fair=equity/shares
        upside=(fair/price-1)*100
        scenarios.append({"name":name,"ev_ebitda_assumption":multiple,"equity_value_rub":round(equity),
                          "value_per_share":round(fair,2),"upside_pct":round(upside,1)})
    base=scenarios[1];mos=base["upside_pct"]
    if mos>=20: state,light="UNDERVALUED","GREEN"
    elif mos<=-20: state,light="OVERVALUED","RED"
    else: state,light="FAIR_RANGE","YELLOW"
    return {"status":"OK","price":round(price,2),"market_cap_rub":round(market_cap),"net_debt_rub":round(net_debt),
            "enterprise_value_rub":round(ev),"ebitda_basis_rub":round(ebitda),"ebitda_basis":"VK 2026 guidance >24bn RUB; conservative floor uses 24bn",
            "current_ev_ebitda":round(ev_ebitda,2),"scenarios":scenarios,"base_value_per_share":base["value_per_share"],
            "margin_of_safety_pct":mos,"valuation_state":state,"light":light,
            "method":"EV/EBITDA scenario valuation","confidence":"LOW","confidence_reason":"Scenario multiples are not yet validated against comparable-company or VK historical trading multiples.","assumption_note":"4x/6x/8x are explicit Bear/Base/Bull analytical assumptions, not observed peer multiples or analyst targets.",
            "conclusion":f"At {price:.2f} RUB, implied EV/EBITDA is {ev_ebitda:.2f}x. Base 6x scenario gives {base['value_per_share']:.2f} RUB/share ({mos:+.1f}%).",
            "read_only":True}
