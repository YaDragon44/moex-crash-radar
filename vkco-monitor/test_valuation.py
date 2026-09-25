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

def test_market_evidence_is_context_only():
    x=valuation.build(113.55,{"issue_size":572904180},{"facts":{"net_debt_bln":60.2,"guidance_ebitda_2026_bln":24}})
    assert x["market_evidence"]["peer_median"]==5.205
    assert x["scenarios"][1]["ev_ebitda_assumption"]==6.0

def test_sensitivity_matrix():
    x=valuation.build(112.75,{"issue_size":572904180},{"facts":{"net_debt_bln":60.2,"guidance_ebitda_2026_bln":24}})
    assert [r["ebitda_bln"] for r in x["sensitivity"]]==[24.0,26.0,28.0]
    assert [v["multiple"] for v in x["sensitivity"][0]["values"]]==[4.0,5.0,6.0,7.0,8.0]
    assert x["sensitivity"][0]["values"][0]["value_per_share"] < x["sensitivity"][2]["values"][-1]["value_per_share"]
