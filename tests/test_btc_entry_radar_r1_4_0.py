from scripts.btc_entry_radar_r1_4_0 import EntryRadarInput, evaluate


def test_no_trade_on_bad_quality():
    r=evaluate(EntryRadarInput(None,None,None,"N/A",None,False))
    assert r.state=="NO_TRADE" and r.standard_size==0


def test_watch_while_new_low():
    r=evaluate(EntryRadarInput(20,False,True,"DELEVERAGING",1.0,True))
    assert r.state=="WATCH"


def test_armed_after_low_stops_before_confirmation():
    r=evaluate(EntryRadarInput(30,False,False,"STABLE",1.2,True))
    assert r.state=="ARMED"


def test_long_ready_best_case():
    r=evaluate(EntryRadarInput(20,True,False,"DELEVERAGING",1.0,True))
    assert r.state=="LONG_READY" and r.standard_size==1.0


def test_long_ready_reduced_for_build():
    r=evaluate(EntryRadarInput(30,True,False,"MODERATE_BUILD",1.0,True))
    assert r.state=="LONG_READY" and r.standard_size==0.5


def test_no_trade_overheated():
    r=evaluate(EntryRadarInput(20,True,False,"OVERHEATED",1.0,True))
    assert r.state=="NO_TRADE"


def test_no_trade_stop_too_wide():
    r=evaluate(EntryRadarInput(20,True,False,"DELEVERAGING",2.1,True))
    assert r.state=="NO_TRADE"


def test_manage_open_position():
    r=evaluate(EntryRadarInput(75,True,False,"OVERHEATED",1.0,True,True))
    assert r.state=="MANAGE"
