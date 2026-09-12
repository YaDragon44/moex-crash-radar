import os

from trade_plan import build_trade_plan, format_trade_plan


def signal(entry=120.0, stop=116.0):
    return {"entry": entry, "stop": stop}


def test_trade_plan_calculates_position_size(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    p = build_trade_plan(signal())
    assert p["allowed_risk"] == 5000.0
    assert p["shares"] == 1250
    assert p["actual_risk"] == 5000.0
    assert p["position_value"] == 150000.0
    assert p["sizing_ready"] is True


def test_trade_plan_without_capital_is_safe(monkeypatch):
    monkeypatch.delenv("TRADING_CAPITAL_RUB", raising=False)
    monkeypatch.delenv("RISK_PCT", raising=False)
    p = build_trade_plan(signal())
    assert p["sizing_ready"] is False
    assert p["shares"] is None


def test_invalid_long_stop_rejected(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    try:
        build_trade_plan(signal(entry=120, stop=121))
        assert False
    except ValueError:
        assert True


def test_format_contains_actionable_risk(monkeypatch):
    monkeypatch.setenv("TRADING_CAPITAL_RUB", "1000000")
    monkeypatch.setenv("RISK_PCT", "0.5")
    text = format_trade_plan(signal())
    assert "Размер позиции" in text
    assert "Фактический риск" in text
