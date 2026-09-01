from pathlib import Path

HTML = Path('web/simple-entry-radar/live.html').read_text(encoding='utf-8')
PAGES = Path('.github/workflows/pages.yml').read_text(encoding='utf-8')


def test_live_universe_and_rollover_contract():
    for label in ['MX','Si','SBER','GD','BR','MMU','CRU','SVU','NG','GAZP','ROSN','T','Silver']:
        assert repr(label) in HTML or f"'{label}'" in HTML
    assert 'LASTTRADEDATE' in HTML
    assert 'resolve()' in HTML
    assert "startsWith(p)" in HTML


def test_strong_signal_is_fail_closed():
    assert 'BLOCKED_AUTH' in HTML
    assert 'oiOK&&po&&rvOK&&rOK&&tOK' in HTML
    assert "st='STRONG '+dir" in HTML
    assert "oi_delta_pct" in HTML
    assert "legal_net_delta" in HTML
    assert "retail_net_delta" in HTML


def test_thresholds_remain_frozen():
    assert 'x>=.5' in HTML
    assert 'rv>=1.2' in HTML
    assert 'R>=55&&R<=65&&R>Rp' in HTML
    assert 'R>=35&&R<=45&&R<Rp' in HTML


def test_pages_publishes_entry_radar():
    assert 'mkdir -p _site/simple-entry-radar' in PAGES
    assert 'web/simple-entry-radar/live.html _site/simple-entry-radar/index.html' in PAGES
