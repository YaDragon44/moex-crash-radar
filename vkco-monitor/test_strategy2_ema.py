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


def crossing_values(direction):
    values = [100.0] * 200
    values += ([80.0] * 100 if direction == "BUY" else [120.0] * 100)
    step = 200.0 if direction == "BUY" else 20.0
    for _ in range(100):
        values.append(step)
        if s2.evaluate(candles(values))["signal"] == direction:
            return values
    raise AssertionError(f"{direction} crossover not produced")


def test_buy_cross():
    r = s2.evaluate(candles(crossing_values("BUY")))
    assert r["signal"] == "BUY"
    assert r["ema50"] > r["ema200"]


def test_sell_cross():
    r = s2.evaluate(candles(crossing_values("SELL")))
    assert r["signal"] == "SELL"
    assert r["ema50"] < r["ema200"]


def test_shadow_buy_then_sell_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(s2, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(s2, "JOURNAL_FILE", tmp_path / "journal.jsonl")
    buy = crossing_values("BUY")
    rb = s2.run_shadow(candles(buy))
    assert rb["journal_appended"] is True
    assert s2._load_state()["position"]["entry"] == buy[-1]
    sell = crossing_values("SELL")
    rs = s2.run_shadow(candles(sell))
    assert rs["journal_appended"] is True
    assert s2._load_state()["position"] is None
    rows = s2.load_journal()
    assert [r["action"] for r in rows] == ["OPEN_LONG", "CLOSE_LONG"]
