from __future__ import annotations
from typing import Any

# Transparent scenario assumptions, not market-consensus targets.
# Scenario multiples remain explicit assumptions until comparable-company evidence is available.
# Public market evidence snapshot (2026-09): Smart-Lab sector table shows
# VKCO 2026Q2 6.60x, HEAD 5.58x, YDEX 4.83x. T-Investments independently
# estimated VKCO forward 2026 EV/EBITDA around 7.6x. These are context, not inputs.
MARKET_EVIDENCE={
 "as_of":"2026-09","vkco_q2_ev_ebitda":6.60,
 "peers":[{"ticker":"HEAD","ev_ebitda":5.58},{"ticker":"YDEX","ev_ebitda":4.83}],
 "peer_median":5.205,"external_forward_vkco":7.6,
 "sources":[
  {"name":"Smart-Lab IT sector EV/EBITDA table","url":"https://smart-lab.ru/q/shares_fundamental6/?field=ev_ebitda&sector_id%5B%5D=25"},
  {"name":"T-Investments VK valuation note","url":"https://www.tbank.ru/invest/social/profile/T-Investments/vk-spaset-li-vk-tech-ot-zamedleniya-viruchki/"}]}
SCENARIOS=(("BEAR",4.0),("BASE",6.0),("BULL",8.0))

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
    # Sensitivity makes the key valuation uncertainty explicit: EBITDA delivery.
    sensitivity=[]
    for ebitda_bln in (24.0,26.0,28.0):
        row={"ebitda_bln":ebitda_bln,"values":[]}
        for multiple in (4.0,5.0,6.0,7.0,8.0):
            fair=max(multiple*ebitda_bln*1e9-net_debt,0.0)/shares
            row["values"].append({"multiple":multiple,"value_per_share":round(fair,2),
                                  "upside_pct":round((fair/price-1)*100,1)})
        sensitivity.append(row)
    if mos>=20: state,light="POTENTIALLY_UNDERVALUED","YELLOW"
    elif mos<=-20: state,light="POTENTIALLY_OVERVALUED","YELLOW"
    else: state,light="FAIR_RANGE","YELLOW"
    return {"status":"OK","price":round(price,2),"market_cap_rub":round(market_cap),"net_debt_rub":round(net_debt),
            "enterprise_value_rub":round(ev),"ebitda_basis_rub":round(ebitda),"ebitda_basis":"VK 2026 guidance >24bn RUB; conservative floor uses 24bn",
            "current_ev_ebitda":round(ev_ebitda,2),"scenarios":scenarios,"sensitivity":sensitivity,"base_value_per_share":base["value_per_share"],
            "margin_of_safety_pct":mos,"valuation_state":state,"light":light,
            "method":"EV/EBITDA scenario valuation","confidence":"MEDIUM","confidence_reason":"6x base is bracketed by public 2026 sector evidence: HEAD 5.58x, YDEX 4.83x, VKCO 6.60x; T-Investments separately estimated VKCO around 7.6x. Comparability is imperfect, so evidence is context rather than a mechanical peer target.","market_evidence":MARKET_EVIDENCE,"assumption_note":"4x/6x/8x are explicit Bear/Base/Bull analytical assumptions, not observed peer multiples or analyst targets.",
            "conclusion":f"At {price:.2f} RUB, implied EV/EBITDA is {ev_ebitda:.2f}x. Base 6x scenario gives {base['value_per_share']:.2f} RUB/share ({mos:+.1f}%).",
            "read_only":True}
