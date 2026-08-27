from moex_crash_radar.moex import parse_candles


def test_parse_candles_from_iss_shape():
    payload = {
        "candles": {
            "columns": ["begin", "open", "close", "high", "low", "value", "volume"],
            "data": [
                ["2026-08-26 00:00:00", 2100.0, 2050.0, 2120.0, 2040.0, 123456789.0, 987654.0],
                ["2026-08-27 00:00:00", 2055.0, 2080.0, 2090.0, 2035.0, None, None],
            ],
        }
    }
    candles = parse_candles(payload)
    assert len(candles) == 2
    assert candles[0].close == 2050.0
    assert candles[0].volume == 987654.0
    assert candles[1].value is None


def test_parse_candles_skips_incomplete_rows():
    payload = {
        "candles": {
            "columns": ["begin", "open", "close", "high", "low", "value", "volume"],
            "data": [["2026-08-27 00:00:00", None, 2080.0, 2090.0, 2035.0, 1.0, 1.0]],
        }
    }
    assert parse_candles(payload) == []
