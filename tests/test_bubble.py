import pytest

from moex_crash_radar.bubble import BubbleInputs, BubbleState, calculate_bubble


def test_bubble_fails_closed_on_narrow_evidence():
    result = calculate_bubble(BubbleInputs(valuation=95, concentration=90, leverage=85))
    assert result.score is None
    assert result.state == BubbleState.DATA_INSUFFICIENT


def test_bubble_detects_broad_build_up():
    result = calculate_bubble(BubbleInputs(
        valuation=80,
        concentration=75,
        leverage=70,
        crowd_euphoria=72,
        price_stretch=78,
        breadth_fragility=55,
        volatility_complacency=65,
    ))
    assert result.score is not None
    assert result.state in {BubbleState.BUILD_UP, BubbleState.FRAGILE}
    assert len(result.reasons) == 3


def test_bubble_tracks_inflation_velocity_and_persistence():
    result = calculate_bubble(
        BubbleInputs(
            valuation=85,
            concentration=80,
            leverage=82,
            crowd_euphoria=80,
            price_stretch=84,
            breadth_fragility=70,
            volatility_complacency=75,
        ),
        history=[58, 62, 66, 70],
    )
    assert result.state == BubbleState.FRAGILE
    assert result.velocity is not None and result.velocity >= 5
    assert result.transition == "INFLATING_FAST"
    assert result.persistence == 4


def test_bubble_rejects_invalid_scores():
    with pytest.raises(ValueError):
        calculate_bubble(BubbleInputs(
            valuation=101,
            concentration=80,
            leverage=80,
            crowd_euphoria=80,
        ))
