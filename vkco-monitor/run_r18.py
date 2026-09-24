from __future__ import annotations

import os

import monitor
import run_r16
import strategy2_ema
import strategy3_value_rsi
import strategy4_h1
from yandex_consensus import fetch_consensus


def heartbeat() -> int:
    candles = monitor.fetch_candles()
    latest = candles[-1]
    now = monitor.datetime.now(monitor.MOSCOW)
    age_min = int((now - latest.end).total_seconds() // 60)
    fresh = latest.end.date() == now.date() and now - latest.end <= monitor.timedelta(minutes=45)

    if fresh:
        text = (
            "💚 VKCO Monitor R1.8 — HEARTBEAT OK\n"
            f"MOEX latest: {latest.end.isoformat()} MSK\n"
            f"VKCO: {latest.close:.2f} ₽\n"
            f"Data age: {age_min} min"
        )
        status = "OK"
    else:
        text = (
            "🟡 VKCO Monitor R1.8 — HEARTBEAT DEGRADED\n"
            f"MOEX latest: {latest.end.isoformat()} MSK\n"
            f"VKCO: {latest.close:.2f} ₽\n"
            f"Data age: {age_min} min\n"
            "Данные старше 45 минут или относятся не к текущему дню. Новые входы блокируются."
        )
        status = "DEGRADED"

    monitor.send_telegram(text)
    print(f"heartbeat={status} age_min={age_min}")
    return 0


def main() -> int:
    mode = os.getenv("MODE", "run")
    if mode == "heartbeat":
        return heartbeat()
    if mode == "test_telegram":
        monitor.send_telegram("✅ VKCO R1.8 Production: Telegram test OK")
        print("telegram_test=OK")
        return 0
    try:
        s2 = strategy2_ema.run_shadow(monitor.fetch_candles())
        print("strategy2={} ema50={} ema200={} journal_appended={}".format(s2['signal'], s2['ema50'], s2['ema200'], int(s2['journal_appended'])))
    except Exception as exc:
        print(f"strategy2=DEGRADED error={type(exc).__name__}: {exc}")
    try:
        s3 = strategy3_value_rsi.run_shadow(monitor.fetch_candles(), fetch_consensus())
        print("strategy3={} rsi14={} gap={} trend={} journal_appended={}".format(s3['decision'],s3['rsi14'],s3['valuation_gap_pct'],s3['trend'],int(s3['journal_appended'])))
    except Exception as exc:
        print(f"strategy3=DEGRADED error={type(exc).__name__}: {exc}")
    try:
        s4 = strategy4_h1.run_shadow(strategy4_h1.fetch_h1())
        print("strategy4={} H1 support={} resistance={} journal_appended={}".format(s4['decision'],s4['support'],s4['resistance'],int(s4['journal_appended'])))
    except Exception as exc:
        print(f"strategy4=DEGRADED error={type(exc).__name__}: {exc}")
    if run_r16.manage_existing_position_r16():
        return 0
    return monitor.run()


if __name__ == "__main__":
    raise SystemExit(main())
