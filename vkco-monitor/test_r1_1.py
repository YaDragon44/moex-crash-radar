import os
from unittest.mock import patch

import monitor


def test_heartbeat_mode_sends_message(monkeypatch):
    monkeypatch.setenv("MODE", "heartbeat")
    candles = [
        monitor.Candle(
            begin=monitor.datetime.now(monitor.MOSCOW) - monitor.timedelta(minutes=20),
            end=monitor.datetime.now(monitor.MOSCOW) - monitor.timedelta(minutes=10),
            open=118.0, close=118.2, high=118.4, low=117.9, volume=1000,
        )
        for _ in range(25)
    ]
    with patch.object(monitor, "fetch_candles", return_value=candles), patch.object(monitor, "send_telegram") as send:
        assert monitor.run() == 0
        send.assert_called_once()
        assert "HEARTBEAT OK" in send.call_args.args[0]


def test_test_telegram_mode(monkeypatch):
    monkeypatch.setenv("MODE", "test_telegram")
    with patch.object(monitor, "send_telegram") as send:
        assert monitor.run() == 0
        send.assert_called_once()
        assert "Telegram test OK" in send.call_args.args[0]
