from datetime import datetime, timezone
from scripts.r1_5_2_coverage_gate import CoverageRow,evaluate

def d(s): return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
def row(f,e,a=None,q='DELAYED'):
    e=d(e); a=d(a) if a else e
    return CoverageRow(f,e,a,a,q)

def test_no_auth_blocks():
    assert evaluate([],False)['status']=='BLOCKED_AUTH'
def test_one_family_not_ready():
    x=evaluate([row('MX','2025-01-02T10:00:00'),row('MX','2025-08-02T10:00:00')],True)
    assert x['status']=='DATA_LIMITED' and not x['m1_unlocked']
def test_one_period_not_ready():
    x=evaluate([row('MX','2025-01-02T10:00:00'),row('SI','2025-02-02T10:00:00')],True)
    assert x['status']=='DATA_LIMITED'
def test_two_families_two_periods_ready():
    x=evaluate([row('MX','2025-01-02T10:00:00'),row('SI','2025-08-02T10:00:00')],True)
    assert x['status']=='DATA_READY' and x['m1_unlocked'] and x['m2_m3_unlocked']
def test_lookahead_row_excluded():
    r=CoverageRow('SI',d('2025-08-02T10:00:00'),d('2025-08-02T11:00:00'),d('2025-08-02T10:30:00'),'DELAYED')
    x=evaluate([row('MX','2025-01-02T10:00:00'),r],True)
    assert x['status']=='DATA_LIMITED'
def test_stale_not_usable():
    x=evaluate([row('MX','2025-01-02T10:00:00'),row('SI','2025-08-02T10:00:00',q='STALE')],True)
    assert x['status']=='DATA_LIMITED'
