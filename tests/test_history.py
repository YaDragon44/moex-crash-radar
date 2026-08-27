from moex_crash_radar.history import build_daily_evidence, count_false_positive_days, evaluate_episode
from moex_crash_radar.moex import Candle


def candle(day: int, close: float, volume: float = 1000.0) -> Candle:
    d = f"2024-01-{day:02d}" if day <= 31 else f"2024-02-{day-31:02d}"
    return Candle(begin=d, open=close * 1.002, close=close, high=close * 1.01, low=close * 0.99, value=volume * close, volume=volume)


def long_series(n: int, start: float = 100.0, drift: float = -0.4):
    return [candle(i + 1, max(10.0, start + drift * i), 1000 + i * 10) for i in range(n)]


def test_build_daily_evidence_never_uses_future_equity_rows():
    index = long_series(60)
    eq = {"AAA": long_series(60), "BBB": long_series(60, 90.0, -0.2)}
    rows = build_daily_evidence(index, eq, min_equity_coverage=0.5, warmup=51)
    assert rows
    assert rows[0].day == index[51].begin[:10]
    assert rows[-1].day == index[-1].begin[:10]

    # Append a dramatic future candle. Earlier evidence must not change.
    future = Candle(begin="2024-03-10", open=1, close=1, high=2, low=0.5, value=1, volume=999999)
    eq2 = {k: list(v) + [future] for k, v in eq.items()}
    rows2 = build_daily_evidence(index, eq2, min_equity_coverage=0.5, warmup=51)
    assert rows == rows2


def test_insufficient_coverage_suppresses_market_score():
    index = long_series(60)
    # Four configured names, only one has usable same-day history => 25% coverage.
    eq = {
        "AAA": long_series(60),
        "BBB": long_series(20),
        "CCC": long_series(10),
        "DDD": long_series(5),
    }
    rows = build_daily_evidence(index, eq, min_equity_coverage=0.70, warmup=51)
    assert rows
    assert rows[-1].coverage <= 0.25
    assert rows[-1].score is None
    assert rows[-1].state == "DATA_INSUFFICIENT"


def test_episode_metrics_and_false_positive_counter():
    index = long_series(60, 100.0, -1.0)
    eq = {f"T{i}": long_series(60, 100.0 - i, -1.0) for i in range(6)}
    rows = build_daily_evidence(index, eq, min_equity_coverage=0.5, warmup=51)
    ep = evaluate_episode(rows, name="synthetic", start=rows[0].day, end=rows[-1].day)
    assert ep.trough == rows[-1].day
    cash, false_cash = count_false_positive_days(rows, horizon_days=3, drawdown_threshold_pct=-1.0)
    assert false_cash <= cash
