import math
import pytest

from moex_crash_radar import (
    BottomState,
    CrashState,
    DataQuality,
    Signal,
    breadth_divergence,
    calculate_bottom,
    calculate_crash,
    crash_momentum,
    downside_velocity,
)


def crash_fixture(score=70, quality=DataQuality.LIVE):
    keys = [
        "market_structure",
        "breadth",
        "volume_distribution",
        "volatility_liquidity",
        "levels_momentum",
        "rate_ofz",
        "oil_rub",
        "macro_earnings",
        "news_geopolitics",
    ]
    return {k: Signal(score, quality) for k in keys}


def bottom_fixture(score=75, quality=DataQuality.LIVE):
    keys = [
        "selling_climax",
        "volume_absorption",
        "breadth_divergence",
        "momentum_divergence",
        "liquidity_sweep_reclaim",
        "choch_bos_up",
        "news_non_response",
    ]
    return {k: Signal(score, quality) for k in keys}


def test_signal_range_validation():
    with pytest.raises(ValueError):
        Signal(101)


def test_crash_score_and_cash_gate():
    result = calculate_crash(crash_fixture(70))
    assert result.score == 70
    assert result.state == CrashState.HIGH_RISK
    assert result.critical_confirmations == 4
    assert result.cash_signal is True


def test_crash_does_not_trigger_cash_without_confluence():
    signals = crash_fixture(70)
    signals["market_structure"] = Signal(40)
    signals["breadth"] = Signal(40)
    result = calculate_crash(signals)
    assert result.score is not None
    assert result.critical_confirmations == 2
    assert result.cash_signal is False


def test_missing_data_returns_insufficient_instead_of_inventing_score():
    signals = {
        "market_structure": Signal(90),
        "breadth": Signal(90),
        "volume_distribution": Signal(90, DataQuality.STALE),
    }
    result = calculate_crash(signals)
    assert result.score is None
    assert result.state == CrashState.DATA_INSUFFICIENT
    assert result.cash_signal is False


def test_delayed_data_propagates_quality():
    signals = crash_fixture(20)
    signals["breadth"] = Signal(20, DataQuality.DELAYED)
    result = calculate_crash(signals)
    assert result.quality == DataQuality.DELAYED
    assert result.state == CrashState.NORMAL


def test_bottom_buyback_requires_structure_confirmations():
    signals = bottom_fixture(80)
    result = calculate_bottom(signals)
    assert result.state == BottomState.ACCUMULATION
    assert result.buy_back_signal is True

    signals["liquidity_sweep_reclaim"] = Signal(20)
    signals["choch_bos_up"] = Signal(20)
    result2 = calculate_bottom(signals)
    assert result2.buy_back_signal is False


def test_crash_momentum():
    assert crash_momentum([20, 25, 30, 35, 40, 45], lookback=5) == 25
    assert crash_momentum([20, 25], lookback=5) is None


def test_downside_velocity():
    result = downside_velocity([100, 99, 98, 96, 94, 90], lookback=5)
    assert result == -10.0


def test_breadth_divergence_detects_internal_deterioration():
    assert breadth_divergence(
        index_returns=[0.1, 0.0, -0.1, 0.1, 0.0],
        breadth_returns=[-1.2, -1.0, -1.1, -1.0, -1.0],
        window=5,
    ) is True


def test_breadth_divergence_rejects_joint_selloff():
    assert breadth_divergence(
        index_returns=[-1.0, -1.0, -1.0, -1.0, -1.0],
        breadth_returns=[-1.2, -1.0, -1.1, -1.0, -1.0],
        window=5,
    ) is False
