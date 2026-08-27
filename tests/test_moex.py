import json
from urllib.error import URLError

import moex_crash_radar.moex as moex
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


class _Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_get_json_retries_transient_failure(monkeypatch):
    calls = {"n": 0}
    def fake_urlopen(req, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise URLError("temporary timeout")
        return _Response({"ok": True})
    monkeypatch.setattr(moex, "urlopen", fake_urlopen)
    monkeypatch.setattr(moex.time, "sleep", lambda _: None)
    assert moex._get_json("https://iss.moex.com/test", attempts=3) == {"ok": True}
    assert calls["n"] == 2


def test_get_json_raises_after_retry_budget(monkeypatch):
    calls = {"n": 0}
    def fake_urlopen(req, timeout):
        calls["n"] += 1
        raise URLError("still unavailable")
    monkeypatch.setattr(moex, "urlopen", fake_urlopen)
    monkeypatch.setattr(moex.time, "sleep", lambda _: None)
    try:
        moex._get_json("https://iss.moex.com/test", attempts=3)
    except URLError:
        pass
    else:
        raise AssertionError("URLError expected")
    assert calls["n"] == 3
