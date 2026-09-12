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
    with patch.object(monitor, "fetch_candles", return_value=_candles(10)), patch.object(monitor, "send_telegram") as send:
        assert run_r18.heartbeat() == 0
        send.assert_called_once()
        assert "HEARTBEAT OK" in send.call_args.args[0]


def test_r18_heartbeat_degraded_for_stale_data():
    with patch.object(monitor, "fetch_candles", return_value=_candles(60)), patch.object(monitor, "send_telegram") as send:
        assert run_r18.heartbeat() == 0
        send.assert_called_once()
        assert "HEARTBEAT DEGRADED" in send.call_args.args[0]
        assert "Новые входы блокируются" in send.call_args.args[0]
