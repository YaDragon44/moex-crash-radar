from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.moex import Candle


def _series(count: int, *, start: float = 100.0) -> list[Candle]:
    rows = []
    for i in range(count):
        day = f"2024-01-{i + 1:02d}" if i < 31 else f"2024-02-{i - 30:02d}"
        close = start + i * 0.1
        rows.append(Candle(day, close, close, close + 1, close - 1, close * 1000, 1000.0))
    return rows


def test_future_constituent_change_never_rewrites_prior_breadth_coverage():
    index = _series(60)
    equities = {"AAA": _series(60), "BBB": _series(10, start=50.0)}
    base = {"2024-01-01": ("AAA",)}
    with_future_change = {**base, "2024-03-01": ("AAA", "BBB")}

    rows = build_daily_evidence(index, equities, warmup=51, min_equity_coverage=0.70, universe_by_effective_date=base)
    future_rows = build_daily_evidence(index, equities, warmup=51, min_equity_coverage=0.70, universe_by_effective_date=with_future_change)

    assert rows == future_rows
    assert all(row.coverage == 1.0 for row in rows)
