from moex_crash_radar.context_validation import (
    HistoricalContextPoint,
    _point_in_time_return,
)


def test_point_in_time_return_uses_only_available_days():
    series = {
        "2024-01-01": 100.0,
        "2024-01-02": 102.0,
        "2024-01-03": 104.0,
        "2024-01-04": 208.0,
    }
    value = _point_in_time_return(series, "2024-01-03", 2)
    assert round(value, 2) == 4.0


def test_historical_context_point_explicitly_allows_na():
    point = HistoricalContextPoint(
        day="2024-01-01",
        score=None,
        coverage=0.35,
        rate_ofz_score=50.0,
        oil_rub_score=None,
    )
    assert point.score is None
    assert point.coverage < 0.50
