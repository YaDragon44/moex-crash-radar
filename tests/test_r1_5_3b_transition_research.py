from moex_crash_radar.history import DailyEvidence
from moex_crash_radar.transition_research import model_observations, summarize_model

def _row(day: str, close: float, coverage: float = 1.0) -> DailyEvidence:
    return DailyEvidence(day, close, 0, "LOW", 1, False, 0, coverage, 40, 45, 45, 55)

def test_m4_is_locked_distribution_watch_and_never_uses_insufficient_coverage():
    assert model_observations(_row("2024-01-01", 100), 0)["M4"] is True
    assert all(value is None for value in model_observations(_row("2024-01-01", 100, 0.69), 0).values())

def test_summary_uses_only_complete_forward_horizon_and_reports_research_metrics():
    rows = [_row(f"2024-01-{day:02d}", 100 if day <= 10 else 90) for day in range(1, 31)]
    result = summarize_model(rows, "M4", start="2024-01-01", end="2024-12-31")
    assert result["usable_rows"] == 5
    assert result["alert_rows"] == 5
    assert result["true_positive_rows"] == 5
