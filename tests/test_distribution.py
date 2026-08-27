from moex_crash_radar.distribution import calculate_distribution, distribution_signal
from moex_crash_radar.moex import Candle


def series(down: bool, high_last_volume: bool, n: int = 30):
    out = []
    price = 100.0
    for i in range(n):
        open_ = price
        close = price - 1 if down else price + 1
        volume = 1000.0
        if high_last_volume and i == n - 1:
            volume = 2000.0
        out.append(Candle(str(i), open_, close, max(open_, close) + 1, min(open_, close) - 1, None, volume))
        price = close
    return out


def test_distribution_signal_high_on_broad_down_volume():
    universe = {"A": series(True, True), "B": series(True, True), "C": series(True, True)}
    snap = calculate_distribution(universe)
    assert snap is not None
    assert snap.pct_down_rvol == 100.0
    assert snap.pct_distribution_5d == 100.0
    assert distribution_signal(snap).score >= 80


def test_distribution_signal_low_on_up_market():
    universe = {"A": series(False, False), "B": series(False, False), "C": series(False, False)}
    snap = calculate_distribution(universe)
    assert snap is not None
    assert snap.pct_down_rvol == 0.0
    assert snap.pct_distribution_5d == 0.0
    assert distribution_signal(snap).score == 0.0
