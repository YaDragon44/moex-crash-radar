from moex_crash_radar.market_risk import (
    IndependentMarketRiskInputs,
    MarketRisk,
    calculate_independent_market_risk,
)


def test_market_risk_fails_closed_with_insufficient_groups():
    result = calculate_independent_market_risk(
        IndependentMarketRiskInputs(market_structure=80, breadth=70)
    )
    assert result.score is None
    assert result.state == MarketRisk.DATA_INSUFFICIENT


def test_market_risk_detects_high_stress():
    result = calculate_independent_market_risk(
        IndependentMarketRiskInputs(
            market_structure=80,
            breadth=85,
            volatility_liquidity=75,
            volume_distribution=70,
        )
    )
    assert result.score is not None
    assert result.state in {MarketRisk.HIGH, MarketRisk.CRITICAL}
    assert result.available_groups == 4


def test_market_risk_velocity_is_independent_transition_signal():
    result = calculate_independent_market_risk(
        IndependentMarketRiskInputs(
            market_structure=65,
            breadth=70,
            volatility_liquidity=70,
            volume_distribution=60,
        ),
        prior_score=50,
    )
    assert result.velocity is not None
    assert result.direction == "RISING_FAST"


def test_market_risk_validates_input_range():
    try:
        calculate_independent_market_risk(
            IndependentMarketRiskInputs(
                market_structure=101,
                breadth=70,
                volatility_liquidity=70,
            )
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
