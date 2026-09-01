from pathlib import Path

HTML = Path('web/simple-entry-radar/index.html').read_text(encoding='utf-8')
README = Path('web/simple-entry-radar/README.md').read_text(encoding='utf-8')


def test_universe_is_frozen_to_13_markets():
    for token in ['MXU6','SiU6','SRU6','GDU6','BRU6','MMU6','CRU6','SVU6','NGU6','GZU6','RNU6','TBU6','SLVRUBF']:
        assert token in HTML
    assert '0/13' in HTML


def test_strong_thresholds_are_present():
    assert "oiDelta>=.5" in HTML
    assert "rv>=1.2" in HTML
    assert "r>=55&&r<=65" in HTML
    assert "r>=35&&r<=45" in HTML
    assert "px>entry" in HTML
    assert "px<entry" in HTML


def test_fail_closed_positioning_gate():
    assert "Legal/FIZ unavailable" in HTML
    assert "&&posOK" in HTML
    assert "Missing Legal/FIZ" in HTML
    assert "fail-closed" in README


def test_no_fake_position_values_are_bundled():
    assert not Path('web/simple-entry-radar/positions.json').exists()
