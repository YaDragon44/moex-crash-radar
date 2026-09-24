from unittest.mock import patch

import monitor
import run_r18


def _candles(minutes_old: int):
    now = monitor.datetime.now(monitor.MOSCOW)
    return [
        monitor.Candle(
            begin=now - monitor.timedelta(minutes=minutes_old + 10),
            end=now - monitor.timedelta(minutes=minutes_old),
            open=118.0,
            close=118.2,
            high=118.4,
            low=117.9,
            volume=1000,
        )
        for _ in range(25)
    ]


def test_r18_heartbeat_ok_for_fresh_data():
    fixed = monitor.datetime(2026, 9, 24, 15, 0, tzinfo=monitor.MOSCOW)
    fresh = [monitor.Candle(fixed-monitor.timedelta(minutes=20), fixed-monitor.timedelta(minutes=10),118,118.2,118.4,117.9,1000) for _ in range(25)]
    with patch.object(monitor, "fetch_candles", return_value=fresh), patch.object(run_r18.monitor.datetime, "now", return_value=fixed), patch.object(monitor, "send_telegram") as send:
        assert run_r18.heartbeat() == 0
        send.assert_called_once()
        assert "HEARTBEAT OK" in send.call_args.args[0]


def test_r18_heartbeat_degraded_for_stale_data():
    with patch.object(monitor, "fetch_candles", return_value=_candles(60)), patch.object(monitor, "send_telegram") as send:
        assert run_r18.heartbeat() == 0
        send.assert_called_once()
        assert "HEARTBEAT DEGRADED" in send.call_args.args[0]
        assert "Новые входы блокируются" in send.call_args.args[0]
