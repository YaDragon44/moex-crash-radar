from diamond import build

F={"status":"OK","indicators":[{"light":"GREEN"} for _ in range(6)]}
V={"status":"OK","margin_of_safety_pct":30.4}

def test_confirmed_with_valuation_fundamentals_and_technical():
    x=build(F,V,{"status":"WAIT"},{"position":{"entry":112.55}},{"decision":"WAIT"})
    assert x["state"]=="DIAMOND_CONFIRMED"
    assert x["technical_confirmations"]==1
    assert x["read_only"] is True

def test_candidate_without_technical_confirmation():
    x=build(F,V,{"status":"WAIT"},{"signal":"NONE"},{"decision":"WAIT"})
    assert x["state"]=="DIAMOND_CANDIDATE"

def test_no_diamond_without_margin_of_safety():
    x=build(F,{"status":"OK","margin_of_safety_pct":10},{"status":"READY"},{},{"decision":"WAIT"})
    assert x["state"]=="NO_DIAMOND"

def test_fail_closed_without_fundamental_data():
    x=build({"status":"DATA_UNAVAILABLE"},V,{}, {}, {})
    assert x["status"]=="DATA_UNAVAILABLE"
