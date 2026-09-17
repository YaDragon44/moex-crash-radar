from datetime import datetime, timezone
import sys
sys.path.append('scripts')
from r1_5_2_authenticated_futoi_adapter import adapt_futoi_rows, paired_positioning

DT=lambda s: datetime.fromisoformat(s.replace('Z','+00:00'))
DEC=DT('2026-09-13T12:10:00Z')


def row(group='FIZ',moment='2026-09-13T12:00:00Z',systime='2026-09-13T12:00:05Z',ticker='SiU6'):
    return {'TICKER':ticker,'CLGROUP':group,'POS':100 if group=='FIZ' else -100,'POS_LONG':150 if group=='FIZ' else 50,'POS_SHORT':-50 if group=='FIZ' else -150,'MOMENT':moment,'SYSTIME':systime}


def test_missing_auth_is_blocked():
    r=adapt_futoi_rows([row()],DEC,False)
    assert r.quality=='BLOCKED_AUTH' and not r.rows


def test_no_lookahead():
    r=adapt_futoi_rows([row(systime='2026-09-13T12:11:00Z')],DEC,True)
    assert r.quality=='N/A' and not r.rows


def test_duplicate_is_deduplicated():
    x=row(); r=adapt_futoi_rows([x,x],DEC,True)
    assert r.quality=='LIVE' and len(r.rows)==1


def test_missing_pair_does_not_create_positioning():
    r=adapt_futoi_rows([row('FIZ')],DEC,True)
    assert paired_positioning(r.rows)==[]


def test_cross_time_pairing_forbidden():
    rows=[row('FIZ','2026-09-13T12:00:00Z','2026-09-13T12:00:05Z'),row('YUR','2026-09-13T12:05:00Z','2026-09-13T12:05:05Z')]
    r=adapt_futoi_rows(rows,DEC,True)
    assert paired_positioning(r.rows)==[]


def test_exact_fiz_yur_pair_is_usable():
    rows=[row('FIZ'),row('YUR')]
    r=adapt_futoi_rows(rows,DEC,True)
    p=paired_positioning(r.rows)
    assert len(p)==1
    assert p[0]['fiz_net']==100
    assert p[0]['yur_net']==-100
    assert p[0]['fiz_gross']==200
    assert p[0]['yur_gross']==200


def test_out_of_order_input_is_stable():
    rows=[row('YUR'),row('FIZ')]
    r=adapt_futoi_rows(rows,DEC,True)
    assert len(paired_positioning(r.rows))==1
