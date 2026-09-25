import valuation
def test_valuation_contract():
    x=valuation.build(113.75,{"issue_size":572904180},{"facts":{"net_debt_bln":60.2,"guidance_ebitda_2026_bln":24}})
    assert x["status"]=="OK" and x["read_only"] is True
    assert x["current_ev_ebitda"]>0 and len(x["scenarios"])==3
    assert x["scenarios"][0]["value_per_share"]<x["scenarios"][1]["value_per_share"]<x["scenarios"][2]["value_per_share"]
def test_fail_closed():
    assert valuation.build(0,{},{} )["status"]=="DATA_UNAVAILABLE"
\ndef test_unvalidated_scenario_is_not_green():\n    x=valuation.build(113.55,{"issue_size":572904180},{"facts":{"net_debt_bln":60.2,"guidance_ebitda_2026_bln":24}})\n    assert x["confidence"]=="LOW"\n    assert x["light"]=="YELLOW"\n    assert x["valuation_state"].startswith("POTENTIALLY_") or x["valuation_state"]=="FAIR_RANGE"\n