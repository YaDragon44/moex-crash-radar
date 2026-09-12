from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from monitor import Candle, adaptive_levels, apply_market_filter, detect_signal, market_filter

MSK = ZoneInfo("Europe/Moscow")
BASE = datetime(2026, 9, 11, 12, 0, tzinfo=MSK)


def c(i, o, h, l, close, v=1000):
    begin = BASE + timedelta(minutes=10 * i)
    return Candle(begin, begin + timedelta(minutes=10), o, close, h, l, v)


def base20(close=100.0):
    return [c(i, close, 101.0, 99.0, close, 1000) for i in range(20)]


def test_adaptive_levels_use_previous_20_candles():
    xs = base20() + [c(20, 100, 102, 99.5, 101), c(21, 101, 103, 100, 102), c(22, 102, 104, 101, 103)]
    lv = adaptive_levels(xs)
    assert lv["support"] == 99.0
    assert lv["resistance"] == 101.0


def test_adaptive_breakout_requires_two_closes_and_volume():
    xs = base20() + [
        c(20, 100.0, 101.0, 99.5, 100.8, 1000),
        c(21, 101.0, 102.5, 100.8, 102.0, 1400),
        c(22, 102.0, 103.0, 101.4, 102.4, 1100),
    ]
    s = detect_signal(xs)
    assert s and s["kind"] == "ADAPTIVE_BREAKOUT"
    assert s["resistance"] == 101.0
    assert s["rvol"] >= 1.2


def test_breakout_without_volume_is_rejected():
    xs = base20() + [
        c(20, 100.0, 101.0, 99.5, 100.8, 1000),
        c(21, 101.0, 102.5, 100.8, 102.0, 1100),
        c(22, 102.0, 103.0, 101.4, 102.4, 1100),
    ]
    assert detect_signal(xs) is None


def test_adaptive_spring_requires_reclaim_hold_and_volume():
    xs = base20() + [
        c(20, 100.0, 100.5, 99.2, 99.8, 1000),
        c(21, 99.5, 100.5, 98.4, 99.6, 1500),
        c(22, 99.7, 101.0, 99.1, 100.2, 1200),
    ]
    s = detect_signal(xs)
    assert s and s["kind"] == "ADAPTIVE_SPRING"
    assert s["support"] == 99.0


def test_spring_without_hold_is_rejected():
    xs = base20() + [
        c(20, 100.0, 100.5, 99.2, 99.8, 1000),
        c(21, 99.5, 100.5, 98.4, 99.6, 1500),
        c(22, 99.4, 100.0, 98.8, 99.0, 1200),
    ]
    assert detect_signal(xs) is None


def test_market_filter_accepts_stable_imoex():
    xs = [c(i, 100.0, 100.2, 99.8, 100.0, 0) for i in range(21)]
    m = market_filter(xs)
    assert m["ok"] is True
    assert m["score"] == 2


def test_market_filter_blocks_selloff():
    xs = [c(i, 100.0, 100.2, 99.8, 100.0, 0) for i in range(20)]
    xs.append(c(20, 98.0, 98.2, 97.8, 98.0, 0))
    m = market_filter(xs)
    assert m["ok"] is False
    assert m["score"] == 0


def test_market_score_is_added_to_signal():
    xs = base20() + [
        c(20, 100.0, 101.0, 99.5, 100.8, 1000),
        c(21, 101.0, 102.5, 100.8, 102.0, 1400),
        c(22, 102.0, 103.0, 101.4, 102.4, 1100),
    ]
    s = detect_signal(xs)
    assert s is not None
    enriched = apply_market_filter(s, {"ok": True, "score": 2, "close": 3000, "sma20": 2990, "return_1h_pct": 0.2, "time": "x"})
    assert enriched["score"] == s["score"] + 2
