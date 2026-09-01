from pathlib import Path

HTML = Path('web/simple-entry-radar/live.html').read_text(encoding='utf-8')
PAGES = Path('.github/workflows/pages.yml').read_text(encoding='utf-8')


def test_universe_and_autorollover():
    for label in ['MX','Si','SBER','GD','BR','MMU','CRU','SVU','NG','GAZP','ROSN','T','Silver']:
        assert f"'{label}'" in HTML
    assert 'LASTTRADEDATE' in HTML
    assert 'startsWith(p)' in HTML


def test_fail_closed_futoi_and_simplified_entry_gate():
    assert 'BLOCKED_AUTH' in HTML
    assert "if(dir!=='NONE'&&tOK){st='ENTRY '+dir" in HTML
    assert 'legal_net_delta' in HTML
    assert 'retail_net_delta' in HTML
    assert "ps=['N/A','BLOCKED_AUTH','n']" in HTML


def test_soft_confirmation_thresholds_remain_visible():
    assert 'x>=.5' in HTML
    assert 'rv>=1.2' in HTML
    assert 'R>=55&&R<=65&&R>Rp' in HTML
    assert 'R>=35&&R<=45&&R<Rp' in HTML
    assert 'confirms>=2' in HTML


def test_pages_path_is_published():
    assert '_site/simple-entry-radar' in PAGES
