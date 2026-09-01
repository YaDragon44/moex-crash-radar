from moex_crash_radar.moex import Candle
from moex_crash_radar.public_baseline import BaselineConfig, build_features, run_ablation, run_model, summarize


def _candles(n=120):
    rows = []
    price = 100.0
    for i in range(n):
        # deterministic staircase with alternating pullbacks and periodic volume bursts
        hour = 10 + (i % 8)
        day = 1 + i // 8
        drift = 0.35 if (i // 24) % 2 == 0 else -0.28
        pullback = -0.45 if i % 5 == 0 else 0.0
        open_ = price
        close = price + drift + pullback
        high = max(open_, close) + 0.30
        low = min(open_, close) - 0.30
        volume = 1000 + (700 if i % 7 == 0 else 0) + hour * 3
        rows.append(Candle(
            begin=f"2026-01-{day:02d} {hour:02d}:00:00",
            open=open_, close=close, high=high, low=low, value=None, volume=volume,
        ))
        price = close
    return rows


def test_feature_builder_is_closed_bar_only_and_has_rvol():
    rows = build_features(_candles(), BaselineConfig(rvol_sessions=3))
    assert len(rows) == 120
    assert any(r.rvol is not None for r in rows)
    assert all(r.regime in {"BULL", "BEAR", "RANGE"} for r in rows)


def test_public_baseline_rejects_oi_models():
    try:
        run_model(_candles(), "M2")
    except ValueError as exc:
        assert "M0, M1, M5" in str(exc)
    else:
        raise AssertionError("M2 must not be enabled in public baseline")


def test_ablation_returns_only_public_models():
    result = run_ablation(_candles(), BaselineConfig(rvol_sessions=3))
    assert tuple(result) == ("M0", "M1", "M5")


def test_summary_includes_cost_adjusted_expectancy():
    trades = run_model(_candles(), "M0", BaselineConfig(rvol_sessions=3, fee_bps_round_trip=5, slippage_bps_round_trip=5))
    summary = summarize("M0", trades)
    assert summary.trades == len(trades)
    if trades:
        assert summary.expectancy_r is not None
        assert all(t.net_r <= t.gross_r for t in trades)
