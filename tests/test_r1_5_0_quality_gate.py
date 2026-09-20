from datetime import datetime,timezone,timedelta
from scripts.r1_5_0_quality_gate import Observation,validate,coverage,blocked_futoi

def t(h=0):return datetime(2026,9,10,12,tzinfo=timezone.utc)+timedelta(hours=h)

def test_valid_point_in_time():
 o=Observation('MOEX',t(0),t(1),t(1),'DELAYED',123)
 assert validate(o)==(True,'DELAYED')

def test_reject_lookahead():
 o=Observation('MOEX',t(0),t(2),t(1),'LIVE',123)
 assert validate(o)==(False,'LOOKAHEAD_AVAILABLE_AFTER_DECISION')

def test_blocked_auth_is_fail_closed():
 o=blocked_futoi(t(1)); assert validate(o)==(True,'BLOCKED_AUTH'); assert o.value is None

def test_blocked_auth_cannot_carry_fake_value():
 o=Observation('MOEX_FUTOI',None,None,t(1),'BLOCKED_AUTH',0)
 assert validate(o)[0] is False

def test_na_cannot_be_neutral_value():
 o=Observation('X',None,None,t(1),'N/A',0)
 assert validate(o)[0] is False

def test_coverage_excludes_stale_na_blocked():
 obs=[Observation('A',t(),t(),t(),'LIVE',1),Observation('B',t(),t(),t(),'DELAYED',1),Observation('C',t(),t(),t(),'STALE',1),blocked_futoi(t()),Observation('D',None,None,t(),'N/A',None)]
 c=coverage(obs); assert c['usable']==2 and c['coverage_pct']==40.0 and c['data_ready'] is False
