from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import strategy2_ema as s2

MSK = ZoneInfo("Europe/Moscow")
BASE = datetime(2026, 1, 1, tzinfo=MSK)


def candles(values):
    return [SimpleNamespace(close=v, end=BASE + timedelta(minutes=10*i)) for i, v in enumerate(values)]


def test_ema_constant_series():
    xs = s2.ema([100.0] * 220, 50)
    assert xs[-1] == 100.0


def test_buy_cross():
    values = [100.0] * 200 + [80.0] * 100 + [200.0] * 2
    r = s2.evaluate(candles(values))
    assert r["signal"] == "BUY"
    assert r["ema50"] > r["ema200"]


def test_sell_cross():
    values = [100.0] * 200 + [120.0] * 100 + [20.0] * 2
    r = s2.evaluate(candles(values))
    assert r["signal"] == "SELL"
    assert r["ema50"] < r["ema200"]


def test_shadow_buy_then_sell_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(s2, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(s2, "JOURNAL_FILE", tmp_path / "journal.jsonl")
    buy = [100.0] * 200 + [80.0] * 100 + [200.0] * 2
    rb = s2.run_shadow(candles(buy))
    assert rb["journal_appended"] is True
    assert s2._load_state()["position"]["entry"] == 200.0
    sell = [100.0] * 200 + [120.0] * 100 + [20.0] * 2
    rs = s2.run_shadow(candles(sell))
    assert rs["journal_appended"] is True
    assert s2._load_state()["position"] is None
    rows = s2.load_journal()
    assert [r["action"] for r in rows] == ["OPEN_LONG", "CLOSE_LONG"]
