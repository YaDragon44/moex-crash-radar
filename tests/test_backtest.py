from moex_crash_radar.backtest import BacktestPoint, evaluate_episode


def test_backtest_metrics_on_synthetic_episode():
    # Synthetic fixture: explicitly not historical market data.
    points = [
        BacktestPoint("d0", 100, 30, 0),
        BacktestPoint("d1", 99, 45, 0),
        BacktestPoint("d2", 98, 58, 0),
        BacktestPoint("d3", 94, 65, 0),
        BacktestPoint("d4", 90, 78, 20),
        BacktestPoint("d5", 84, 88, 45),
        BacktestPoint("d6", 80, 91, 68),
        BacktestPoint("d7", 82, 82, 74),
        BacktestPoint("d8", 86, 70, 82),
        BacktestPoint("d9", 100, 40, 90),
    ]
    result = evaluate_episode(points)
    assert result.signal_date == "d2"
    assert result.crash_start_date == "d3"
    assert result.trough_date == "d6"
    assert result.lead_time_points == 1
    assert result.drawdown_pct == -20.0
    assert result.drawdown_after_signal_pct == -18.37
    assert result.max_drawdown_avoided_pct == 18.37
    assert result.buyback_date == "d7"
    assert result.buyback_delay_points == 1
    assert result.recovery_lag_points == 3


def test_backtest_without_crash_signal():
    points = [
        BacktestPoint("d0", 100, 20),
        BacktestPoint("d1", 99, 25),
        BacktestPoint("d2", 98, 30),
    ]
    result = evaluate_episode(points)
    assert result.signal_date is None
    assert result.max_drawdown_avoided_pct is None
