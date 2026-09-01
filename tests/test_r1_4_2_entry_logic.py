from pathlib import Path

HTML = Path('web/simple-entry-radar/live.html').read_text(encoding='utf-8')


def test_universe_is_frozen_to_13_markets():
    for token in ["['MX'", "['Si'", "['SBER'", "['GD'", "['BR'", "['MMU'", "['CRU'", "['SVU'", "['NG'", "['GAZP'", "['ROSN'", "['T'", "['Silver'"]:
        assert token in HTML


def test_hard_gate_is_trend_plus_trigger_only():
    assert 'hard gates: TREND + PRICE TRIGGER' in HTML
    assert "if(dir!=='NONE'&&tOK){st='ENTRY '+dir" in HTML
    assert 'STRONG requires ALL' not in HTML


def test_confirmations_are_soft_and_missing_futoi_is_not_green():
    assert 'confirms>=2' in HTML
    assert "ps=['N/A','BLOCKED_AUTH','n']" in HTML
    assert "oi=['N/A','unavailable','n']" in HTML


def test_late_state_is_rsi_overextension_not_reversal_signal():
    assert "late=dir==='LONG'?R>68:dir==='SHORT'?R<32:false" in HTML
    assert "st='LATE '+dir" in HTML
    assert 'overextended / do not chase' in HTML


def test_states_are_exposed():
    for state in ['CONFIRMED', 'ENTRY', 'WAIT', 'LATE', 'AVOID']:
        assert state in HTML
