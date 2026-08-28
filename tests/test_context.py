from moex_crash_radar.context import ContextState, calculate_context
from moex_crash_radar.engine import DataQuality, Signal


def test_context_fails_closed_without_two_independent_groups():
    result = calculate_context({"rate_ofz": Signal(70, DataQuality.LIVE)})
    assert result.score is None
    assert result.state == ContextState.DATA_INSUFFICIENT
    assert result.quality == DataQuality.NA
    assert result.available_groups == 1


def test_context_requires_at_least_half_weight_coverage():
    result = calculate_context(
        {
            "oil_rub": Signal(70, DataQuality.LIVE),
            "news_geopolitics": Signal(80, DataQuality.LIVE),
        }
    )
    assert result.score is None
    assert result.coverage == 0.40


def test_context_aggregates_without_becoming_probability():
    result = calculate_context(
        {
            "rate_ofz": Signal(80, DataQuality.LIVE),
            "oil_rub": Signal(60, DataQuality.LIVE),
        }
    )
    assert result.score == 71.67
    assert result.state == ContextState.CAUTION
    assert result.quality == DataQuality.LIVE
    assert result.coverage == 0.60


def test_context_propagates_delayed_quality():
    result = calculate_context(
        {
            "rate_ofz": Signal(90, DataQuality.LIVE),
            "macro_earnings": Signal(80, DataQuality.DELAYED),
        }
    )
    assert result.score is not None
    assert result.quality == DataQuality.DELAYED


def test_stale_context_input_is_not_usable():
    result = calculate_context(
        {
            "rate_ofz": Signal(90, DataQuality.STALE),
            "macro_earnings": Signal(80, DataQuality.LIVE),
            "news_geopolitics": Signal(90, DataQuality.LIVE),
        }
    )
    assert result.score is None
    assert result.available_groups == 2
    assert result.coverage == 0.40
