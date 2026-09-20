from moex_crash_radar import futures_data


def test_fetch_futures_candles_builds_forts_hourly_request(monkeypatch):
    captured = {}

    def fake_get_json(url):
        captured["url"] = url
        return {
            "candles": {
                "columns": ["begin", "open", "close", "high", "low", "value", "volume"],
                "data": [["2026-08-31 10:00:00", 100, 101, 102, 99, 12345, 678]],
            }
        }

    monkeypatch.setattr(futures_data, "_get_json", fake_get_json)
    candles = futures_data.fetch_futures_candles(
        "SiU6",
        start="2026-08-31",
        end="2026-09-01",
        interval=60,
    )

    assert len(candles) == 1
    assert candles[0].begin == "2026-08-31 10:00:00"
    url = captured["url"]
    assert "/engines/futures/markets/forts/securities/SiU6/candles.json?" in url
    assert "interval=60" in url
    assert "from=2026-08-31" in url
    assert "till=2026-09-01" in url
