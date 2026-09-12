from datetime import datetime, timedelta

import export_status
import monitor


def candle(i: int) -> monitor.Candle:
    begin = datetime(2026, 9, 11, 10, 0, tzinfo=monitor.MOSCOW) + timedelta(minutes=10 * i)
    return monitor.Candle(
        begin=begin,
        end=begin + timedelta(minutes=9, seconds=59),
        open=118.0 + i / 10,
        high=118.3 + i / 10,
        low=117.8 + i / 10,
        close=118.2 + i / 10,
        volume=1000 + i,
    )


def test_public_candles_compact_contract_and_limit():
    result = export_status._public_candles([candle(i) for i in range(100)])
    assert len(result) == 72
    assert set(result[-1]) == {"t", "end", "o", "h", "l", "c", "v"}
    assert result[-1]["o"] == 127.9
    assert result[-1]["c"] == 128.1
    assert result[-1]["v"] == 1099
    assert result[-1]["t"].endswith("+03:00")


def test_public_candles_never_contains_secrets():
    result = export_status._public_candles([candle(0)])
    text = str(result).lower()
    assert "token" not in text
    assert "chat" not in text
    assert "secret" not in text
