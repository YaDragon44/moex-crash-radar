from moex_crash_radar.breadth import breadth_signal, calculate_breadth, index_vs_breadth_divergence
from moex_crash_radar.moex import Candle


def candles(start: float, step: float, n: int = 60):
    out = []
    value = start
    for i in range(n):
        nxt = value + step
        out.append(Candle(str(i), value, nxt, max(value, nxt) + 1, min(value, nxt) - 1, None, None))
        value = nxt
    return out


def test_breadth_detects_weak_market():
    universe = {
        "A": candles(100, -1.0),
        "B": candles(120, -0.8),
        "C": candles(140, -0.6),
        "D": candles(160, -0.5),
    }
    snap = calculate_breadth(universe)
    assert snap is not None
    assert snap.pct_above_ma20 == 0.0
    assert snap.pct_above_ma50 == 0.0
    assert snap.pct_new_20d_lows == 100.0
    assert breadth_signal(snap).score >= 70


def test_breadth_detects_healthy_market():
    universe = {
        "A": candles(100, 1.0),
        "B": candles(120, 0.8),
        "C": candles(140, 0.6),
    }
    snap = calculate_breadth(universe)
    assert snap is not None
    assert snap.pct_above_ma20 == 100.0
    assert snap.pct_above_ma50 == 100.0
    assert snap.pct_new_20d_highs == 100.0
    assert breadth_signal(snap).score < 20


def test_index_vs_breadth_divergence():
    index = candles(2000, 0.1)
    universe = {"A": candles(100, -1.2), "B": candles(120, -1.1), "C": candles(140, -1.0)}
    snap = calculate_breadth(universe)
    assert snap is not None
    assert index_vs_breadth_divergence(index, snap) is True
