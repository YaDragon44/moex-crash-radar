from datetime import datetime
from types import SimpleNamespace

from position_manager import has_active_position, manage_position, open_position


def candle(low, high, close=120.0):
    return SimpleNamespace(
        low=low,
        high=high,
        close=close,
        end=datetime.fromisoformat("2026-09-14T12:00:00"),
    )


def base_signal():
    return {
        "signal_id": "VKCO:test:1",
        "time": "2026-09-14T10:00:00+03:00",
        "entry": 120.0,
        "stop": 116.0,
        "tp1": 126.0,
        "tp2": 130.0,
        "tp3": 136.0,
        "price": 120.0,
    }


def plan():
    return {"shares": 1250, "lots": 1250, "actual_risk": 5000.0}


def test_open_position_is_active():
    p = open_position(base_signal(), plan())
    assert p["status"] == "OPEN"
    assert has_active_position({"position": p}) is True


def test_tp1_moves_stop_to_breakeven():
    p = open_position(base_signal(), plan())
    p, event = manage_position(p, candle(low=119, high=127, close=126), 1.0)
    assert event == "TP1"
    assert p["status"] == "TP1"
    assert p["stop"] == 120.0


def test_tp2_activates_trailing_and_moves_stop_to_tp1():
    p = open_position(base_signal(), plan())
    p, event = manage_position(p, candle(low=119, high=131, close=130), 1.0)
    assert event == "TP2"
    assert p["status"] == "TRAILING"
    assert p["stop"] == 126.0


def test_trailing_only_moves_stop_up():
    p = open_position(base_signal(), plan())
    p["status"] = "TRAILING"
    p["stop"] = 126.0
    p, event = manage_position(p, candle(low=127, high=133, close=132), 2.0)
    assert event == "TRAILING"
    assert p["stop"] == 129.0


def test_tp3_closes_profit():
    p = open_position(base_signal(), plan())
    p, event = manage_position(p, candle(low=119, high=137, close=136), 1.0)
    assert event == "CLOSED_PROFIT"
    assert p["status"] == "CLOSED_PROFIT"
    assert p["exit_price"] == 136.0


def test_stop_is_conservative_priority_inside_same_candle():
    p = open_position(base_signal(), plan())
    p, event = manage_position(p, candle(low=115, high=137, close=130), 1.0)
    assert event == "CLOSED_STOP"
    assert p["status"] == "CLOSED_STOP"
    assert p["exit_price"] == 116.0
