from moex_crash_radar.context import ContextResult, ContextState
from moex_crash_radar.engine import CrashResult, CrashState, DataQuality
from moex_crash_radar.market_risk import (
    FragilityInput,
    FragilityState,
    MarketRisk,
    calculate_fragility,
    calculate_market_risk,
)


def test_fragility_fails_closed_with_one_group():
    result = calculate_fragility(FragilityInput(valuation=90))
    assert result.score is None
    assert result.state == FragilityState.DATA_INSUFFICIENT


def test_fragility_combines_independent_groups():
    result = calculate_fragility(FragilityInput(valuation=90, concentration=70, leverage=80))
    assert result.score is not None
    assert result.state == FragilityState.EXTREME
    assert result.available_groups == 3


def test_market_risk_keeps_crash_context_fragility_independent():
    crash = CrashResult(70, CrashState.HIGH_RISK, DataQuality.LIVE, 0.72, 3, True)
    context = ContextResult(60, ContextState.CAUTION, DataQuality.LIVE, 0.60, 2, 4)
    fragility = calculate_fragility(FragilityInput(valuation=90, concentration=80, leverage=80))
    result = calculate_market_risk(crash, context, fragility)
    assert result.score is not None
    assert result.state in {MarketRisk.HIGH, MarketRisk.CRITICAL}
    assert result.crash_component == 70
    assert result.context_component == 60
    assert result.fragility_component == fragility.score


def test_market_risk_fails_closed_without_market_core():
    crash = CrashResult(None, CrashState.DATA_INSUFFICIENT, DataQuality.ERROR, 0.4, 0, False)
    context = ContextResult(60, ContextState.CAUTION, DataQuality.LIVE, 0.60, 2, 4)
    fragility = calculate_fragility(FragilityInput(valuation=90, concentration=80))
    result = calculate_market_risk(crash, context, fragility)
    assert result.score is None
    assert result.state == MarketRisk.DATA_INSUFFICIENT
