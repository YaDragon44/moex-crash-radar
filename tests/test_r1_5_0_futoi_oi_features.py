from datetime import datetime, timezone, timedelta
from scripts.r1_5_0_futoi_adapter import FutoiSnapshot, BlockedAuthFutoiAdapter, validate_snapshot
from scripts.r1_5_0_oi_features import build_oi_features

def t(h=0): return datetime(2026,9,10,12,tzinfo=timezone.utc)+timedelta(hours=h)

def test_blocked_adapter_fail_closed():
    x=BlockedAuthFutoiAdapter().get_history('MX',t(),t(1))[0]
    ok,reason=validate_snapshot(x,t(1))
    assert ok and reason=='BLOCKED_AUTH' and x.pos is None

def test_futoi_rejects_lookahead_systime():
    x=FutoiSnapshot('MX','FIZ',10,6,4,t(0),t(2),'LIVE')
    assert validate_snapshot(x,t(1))[0] is False

def test_futoi_accepts_fiz_yur_only():
    x=FutoiSnapshot('MX','FIZ',10,6,4,t(0),t(1),'DELAYED')
    assert validate_snapshot(x,t(1))==(True,'DELAYED')

def test_oi_features_fail_closed_when_blocked():
    x=build_oi_features([100,110],0.01,'BLOCKED_AUTH')
    assert x.oi_total is None and x.price_oi_quadrant=='N/A'

def test_oi_features_up_up():
    x=build_oi_features([100,102,105,110],0.02,'DELAYED')
    assert x.oi_total==110 and x.oi_delta==5 and x.oi_delta_pct>0
    assert x.price_oi_quadrant=='PRICE_UP_OI_UP'
    assert x.oi_persistence==3

def test_oi_features_down_up():
    x=build_oi_features([100,99,101],-0.01,'LIVE')
    assert x.price_oi_quadrant=='PRICE_DOWN_OI_UP'
