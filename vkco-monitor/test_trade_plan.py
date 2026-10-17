from trade_plan import DEFAULT_RISK_PCT, build_trade_plan, format_trade_plan


def signal(entry=120.0, stop=116.0):
    return {"entry": entry, "stop": stop}


def test_trade_plan_calculates_position_size(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    p = build_trade_plan(signal(), lot_size=1)
    assert p["allowed_risk"] == 5000.0
    assert p["shares"] == 1250
    assert p["actual_risk"] == 5000.0
    assert p["position_value"] == 150000.0
    assert p["sizing_ready"] is True


def test_default_risk_pct_is_used_when_missing(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.delenv("RISK_PCT", raising=False)
    p = build_trade_plan(signal(), lot_size=1)
    assert p["risk_pct"] == DEFAULT_RISK_PCT == 0.5
    assert p["allowed_risk"] == 5000.0
    assert p["shares"] == 1250
    assert p["sizing_ready"] is True


def test_trade_plan_without_capital_is_safe(monkeypatch):
    monkeypatch.delenv("TRADING_CAPITAL_RUB", raising=False)
    monkeypatch.delenv("RISK_PCT", raising=False)
    p = build_trade_plan(signal(), lot_size=1)
    assert p["risk_pct"] == 0.5
    assert p["sizing_ready"] is False
    assert p["shares"] is None


def test_invalid_long_stop_rejected(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    try:
        build_trade_plan(signal(entry=120, stop=121), lot_size=1)
        assert False
    except ValueError:
        assert True


def test_format_contains_actionable_risk(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    text = format_trade_plan(signal(), lot_size=1)
    assert "Размер позиции" in text
    assert "Фактический риск" in text


def test_format_without_capital_mentions_only_required_variable(monkeypatch):
    monkeypatch.delenv("TRADING_CAPITAL_RUB", raising=False)
    monkeypatch.delenv("RISK_PCT", raising=False)
    text = format_trade_plan(signal(), lot_size=1)
    assert "0.50%" in text
    assert "TRADING_CAPITAL_RUB" in text
    assert "RISK_PCT" not in text


def test_position_is_capped_by_available_capital(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    p = build_trade_plan(signal(entry=100.0, stop=99.99), lot_size=1)
    assert p["shares"] == 10000
    assert p["position_value"] == 1000000.0
    assert p["actual_risk"] == 100.0
    assert p["sizing_ready"] is True


def test_position_is_rounded_down_to_confirmed_lot(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    p = build_trade_plan(signal(entry=120.0, stop=116.0), lot_size=10)
    assert p["shares"] == 1250
    assert p["lots"] == 125


def test_missing_lot_size_fails_closed(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    try:
        build_trade_plan(signal())
        assert False
    except ValueError as exc:
        assert "LOTSIZE" in str(exc)


def test_invalid_lot_size_fails_closed(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    for lot_size in (0, -1, 1.5, True):
        try:
            build_trade_plan(signal(), lot_size=lot_size)
            assert False
        except ValueError as exc:
            assert "LOTSIZE" in str(exc)
