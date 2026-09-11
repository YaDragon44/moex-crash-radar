from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from monitor import Candle, detect_signal

MSK = ZoneInfo("Europe/Moscow")
BASE = datetime(2026, 9, 11, 12, 0, tzinfo=MSK)


def c(i, o, h, l, close, v=1000):
    begin = BASE + timedelta(minutes=10 * i)
    return Candle(begin, begin + timedelta(minutes=10), o, close, h, l, v)


def filler(n=22, close=135.0):
    return [c(i, close, close + 1, close - 1, close, 1000) for i in range(n)]


def test_breakout_requires_two_closes_above_141():
    xs = filler()
    xs += [c(22, 140, 141, 139, 140.8), c(23, 141, 143, 140.8, 142.0), c(24, 142, 144, 141.2, 143.0)]
    s = detect_signal(xs)
    assert s and s["kind"] == "BREAKOUT_141"


def test_one_close_above_141_is_not_enough():
    xs = filler()
    xs += [c(22, 140, 141, 139, 140.8), c(23, 141, 143, 140.8, 142.0), c(24, 142, 143, 140.2, 140.9)]
    assert detect_signal(xs) is None


def test_confirmed_spring():
    xs = filler()
    xs += [c(22, 132, 133, 131, 132), c(23, 131, 132, 128.2, 130.7, 1800), c(24, 130.8, 132.2, 130.1, 131.6, 1600)]
    s = detect_signal(xs)
    assert s and s["kind"] == "SPRING_127_130"


def test_spring_without_hold_is_rejected():
    xs = filler()
    xs += [c(22, 132, 133, 131, 132), c(23, 131, 132, 128.2, 130.7), c(24, 130.5, 131, 128.7, 129.4)]
    assert detect_signal(xs) is None
