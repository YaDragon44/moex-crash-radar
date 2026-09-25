import valuation
def test_valuation_contract():
    x=valuation.build(113.75,{"issue_size":572904180},{"facts":{"net_debt_bln":60.2,"guidance_ebitda_2026_bln":24}})
    assert x["status"]=="OK" and x["read_only"] is True
    assert x["current_ev_ebitda"]>0 and len(x["scenarios"])==3
    assert x["scenarios"][0]["value_per_share"]<x["scenarios"][1]["value_per_share"]<x["scenarios"][2]["value_per_share"]
def test_fail_closed():
    assert valuation.build(0,{},{} )["status"]=="DATA_UNAVAILABLE"

def test_unvalidated_scenario_is_not_green():
    x=valuation.build(113.55,{"issue_size":572904180},{"facts":{"net_debt_bln":60.2,"guidance_ebitda_2026_bln":24}})
    assert x["confidence"]=="MEDIUM"
    assert x["light"]=="YELLOW"
    assert x["valuation_state"].startswith("POTENTIALLY_") or x["valuation_state"]=="FAIR_RANGE"
\ndef test_market_evidence_is_context_only():\n    x=valuation.build(113.55,{"issue_size":572904180},{"facts":{"net_debt_bln":60.2,"guidance_ebitda_2026_bln":24}})\n    assert x["market_evidence"]["peer_median"]==5.205\n    assert x["scenarios"][1]["ev_ebitda_assumption"]==6.0\n