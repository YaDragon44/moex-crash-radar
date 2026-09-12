from __future__ import annotations

import os

import monitor
import run_r16


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
    if run_r16.manage_existing_position_r16():
        return 0
    return monitor.run()


if __name__ == "__main__":
    raise SystemExit(main())
