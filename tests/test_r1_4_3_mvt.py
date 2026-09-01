from pathlib import Path

HTML = Path('web/simple-entry-radar/live.html').read_text(encoding='utf-8')


def test_mvt_exposes_trade_decision_fields():
    for token in ['R1.4.3 MVT', 'Вход', 'Сейчас', 'ATR14', 'Стоп / риск', 'СВЕЖИЙ', 'АКТИВЕН', 'УСТАРЕЛ']:
        assert token in HTML


def test_stop_is_provisional_not_validated_claim():
    assert 'предв. 1,5×ATR' in HTML
    assert 'Стоп пока предварительный' in HTML
    assert 'Historical Stop Gate' in HTML


def test_wilder_atr_and_risk_distance_exist():
    assert 'a=(a*(n-1)+x)/n' in HTML
    assert 'Math.abs(entry-stop)/entry*100' in HTML


def test_entry_semantics_still_trend_plus_closed_trigger():
    assert "tOK=dir==='LONG'?px>entry:dir==='SHORT'?px<entry:false" in HTML
    assert "if(dir!=='NONE'&&tOK){st='ВХОД '" in HTML
    assert 'RVOL/RSI/OI/юр-физ = подтверждения' in HTML


def test_missing_positioning_is_fail_closed():
    assert "oi=['Н/Д','данные недоступны','n']" in HTML
    assert "ps=['Н/Д','НЕТ ДОСТУПА','n']" in HTML
