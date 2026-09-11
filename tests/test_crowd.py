from moex_crash_radar.crowd import CrowdInputs, CrowdState, calculate_crowd
from moex_crash_radar.crowd_features import (
    breadth_sentiment,
    derive_crowd_inputs,
    momentum_sentiment,
    volatility_sentiment,
    volume_sentiment,
)
from moex_crash_radar.moex import Candle


def candle(i: int, close: float, value: float = 100.0, spread: float = 1.0) -> Candle:
    return Candle(
        begin=f"2026-01-{(i % 28) + 1:02d}",
        open=close - 0.2,
        close=close,
        high=close + spread,
        low=close - spread,
        value=value,
        volume=value,
    )


def series(start: float, step: float, n: int = 60, value: float = 100.0, spread: float = 1.0):
    return [candle(i, start + i * step, value=value, spread=spread) for i in range(n)]


def test_crowd_fails_closed_on_low_coverage():
    result = calculate_crowd(CrowdInputs(breadth_sentiment=80, momentum_sentiment=80))
    assert result.score is None
    assert result.state == CrowdState.DATA_INSUFFICIENT


def test_crowd_extreme_and_velocity():
    result = calculate_crowd(
        CrowdInputs(
            breadth_sentiment=90,
            momentum_sentiment=90,
            volume_sentiment=80,
            volatility_sentiment=85,
        ),
        prior_score=70,
    )
    assert result.score is not None and result.score >= 80
    assert result.state == CrowdState.EUPHORIA
    assert result.extreme is True
    assert result.direction == "RISING_FAST"


def test_momentum_tracks_direction():
    assert momentum_sentiment(series(100, 1.0)) > 50
    assert momentum_sentiment(series(160, -1.0)) < 50


def test_breadth_requires_basket_and_tracks_participation():
    bullish = {f"S{i}": series(100 + i, 1.0) for i in range(5)}
    bearish = {f"S{i}": series(160 + i, -1.0) for i in range(5)}
    assert breadth_sentiment(bullish) == 100.0
    assert breadth_sentiment(bearish) == 0.0
    assert breadth_sentiment({"ONE": series(100, 1.0)}) is None


def test_volume_sentiment_tracks_directional_turnover():
    bullish = {f"S{i}": series(100 + i, 1.0, value=200.0) for i in range(5)}
    bearish = {f"S{i}": series(160 + i, -1.0, value=200.0) for i in range(5)}
    assert volume_sentiment(bullish) == 100.0
    assert volume_sentiment(bearish) == 0.0


def test_volatility_expansion_reduces_sentiment():
    calm = series(100, 0.2, spread=0.5)
    expanding = [candle(i, 100 + i * 0.2, spread=(0.5 if i < 45 else 3.0)) for i in range(60)]
    assert volatility_sentiment(calm) > volatility_sentiment(expanding)


def test_derive_crowd_inputs_keeps_positioning_out():
    equities = {f"S{i}": series(100 + i, 0.5) for i in range(5)}
    inputs = derive_crowd_inputs(series(100, 0.5), equities)
    assert inputs.breadth_sentiment is not None
    assert inputs.momentum_sentiment is not None
    assert inputs.volume_sentiment is not None
    assert inputs.volatility_sentiment is not None
    assert inputs.positioning_sentiment is None
