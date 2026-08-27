from moex_crash_radar.history import DailyEvidence
from moex_crash_radar.live_gate import exit_gate_status


def row(day, close, score, confirmations, breadth=70, volume=70):
    return DailyEvidence(
        day=day,
        close=close,
        score=score,
        state="HIGH_RISK",
        available_weight=0.72,
        cash_signal=False,
        critical_confirmations=confirmations,
        coverage=1.0,
        breadth_score=breadth,
        volume_distribution_score=volume,
    )


def test_live_gate_early_warning_without_price_confirmation():
    evidence = [row(f"2026-01-{i:02d}", 100, 66, 3) for i in range(1, 8)]
    result = exit_gate_status(evidence)
    assert result["stage"] == "EARLY_WARNING"
    assert result["cash_confirmed"] is False


def test_live_gate_exit_watch_after_downside_but_before_persistence():
    evidence = [
        row("2026-01-01", 100, 40, 1),
        row("2026-01-02", 100, 40, 1),
        row("2026-01-03", 100, 40, 1),
        row("2026-01-04", 100, 40, 1),
        row("2026-01-05", 100, 40, 1),
        row("2026-01-06", 96, 66, 3),
    ]
    result = exit_gate_status(evidence)
    assert result["stage"] == "EXIT_WATCH"
    assert result["cash_confirmed"] is False


def test_live_gate_cash_confirmed_after_persistence():
    evidence = [
        row("2026-01-01", 100, 40, 1),
        row("2026-01-02", 100, 40, 1),
        row("2026-01-03", 100, 40, 1),
        row("2026-01-04", 100, 40, 1),
        row("2026-01-05", 100, 40, 1),
        row("2026-01-06", 96, 66, 3),
        row("2026-01-07", 95, 68, 3),
    ]
    result = exit_gate_status(evidence)
    assert result["stage"] == "CASH_CONFIRMED"
    assert result["cash_confirmed"] is True
