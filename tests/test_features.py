from moex_crash_radar.features import derive_index_signals
from moex_crash_radar.moex import Candle


def make_downtrend(n=60):
    candles = []
    price = 3000.0
    for i in range(n):
        close = price - i * 8.0
        candles.append(
            Candle(
                begin=f"d{i}",
                open=close + 5,
                close=close,
                high=close + 12,
                low=close - 12,
                value=None,
                volume=None,
            )
        )
    return candles


def test_index_signals_detect_downtrend_without_fabricating_missing_groups():
    signals = derive_index_signals(make_downtrend())
    assert set(signals) == {"market_structure", "levels_momentum", "volatility_liquidity"}
    assert signals["market_structure"].score >= 70
    assert signals["levels_momentum"].score >= 45
    # Breadth, macro, news, rate and volume are deliberately absent until sourced.
    assert "breadth" not in signals
    assert "macro_earnings" not in signals
