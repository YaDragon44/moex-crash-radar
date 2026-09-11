from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

import requests

TICKER = "VKCO"
BOARD = "TQBR"
INTERVAL = 10
MOSCOW = ZoneInfo("Europe/Moscow")
MOEX_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/shares/boards/"
    f"{BOARD}/securities/{TICKER}/candles.json"
)
STATE_FILE = Path(os.getenv("STATE_FILE", "vkco-monitor/state/state.json"))


@dataclass(frozen=True)
class Candle:
    begin: datetime
    end: datetime
    open: float
    close: float
    high: float
    low: float
    volume: float


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=MOSCOW)


def fetch_candles(days: int = 7) -> list[Candle]:
    date_from = (datetime.now(MOSCOW) - timedelta(days=days)).date().isoformat()
    rows: list[list[Any]] = []
    columns: list[str] | None = None
    offset = 0

    # MOEX ISS ограничивает размер страницы. Забираем все страницы,
    # иначе 7 дней 10m-свечей могут обрезаться на середине периода.
    while True:
        r = requests.get(
            MOEX_URL,
            params={
                "interval": INTERVAL,
                "from": date_from,
                "start": offset,
                "iss.meta": "off",
            },
            timeout=20,
        )
        r.raise_for_status()
        payload = r.json()["candles"]
        if columns is None:
            columns = payload["columns"]
        batch = payload["data"]
        rows.extend(batch)
        if not batch or len(batch) < 500:
            break
        offset += len(batch)
        if offset > 5000:
            raise RuntimeError("Слишком много страниц MOEX candles; safety limit reached")

    if columns is None:
        raise RuntimeError("MOEX не вернул структуру candles")

    out: list[Candle] = []
    now = datetime.now(MOSCOW)
    for row in rows:
        item = dict(zip(columns, row))
        c = Candle(
            begin=_dt(item["begin"]),
            end=_dt(item["end"]),
            open=float(item["open"]),
            close=float(item["close"]),
            high=float(item["high"]),
            low=float(item["low"]),
            volume=float(item.get("volume") or 0),
        )
        if c.end <= now:
            out.append(c)

    if len(out) < 25:
        raise RuntimeError(f"Недостаточно завершенных свечей MOEX: {len(out)}")
    return out


def detect_signal(candles: list[Candle]) -> dict[str, Any] | None:
    a, b, c = candles[-3], candles[-2], candles[-1]
    avg20 = mean(x.volume for x in candles[-21:-1]) or 1.0
    rvol = c.volume / avg20

    # Подтвержденный breakout: до пробоя <=141, затем 2 закрытия подряд >141.
    if a.close <= 141.0 and b.close > 141.0 and c.close > 141.0:
        return _signal("BREAKOUT_141", "Breakout + Hold", c, rvol, stop=136.8,
                       targets=(148.0, 156.0, 165.0), structure=2, level=2, wyckoff=0)

    # Подтвержденный Spring: предыдущая свеча прокалывает 127–130 и закрывается выше 130,
    # следующая удерживает 130 и закрывается не ниже предыдущей.
    if b.low < 130.0 and b.low >= 126.0 and b.close > 130.0 and c.low >= 129.0 and c.close >= b.close:
        return _signal("SPRING_127_130", "Wyckoff Spring / False Breakout", c, rvol,
                       stop=min(126.8, b.low - 0.2), targets=(141.0, 150.0, 158.0),
                       structure=2, level=2, wyckoff=1)
    return None


def _signal(kind: str, setup: str, c: Candle, rvol: float, stop: float,
            targets: tuple[float, float, float], structure: int, level: int, wyckoff: int) -> dict[str, Any]:
    risk = max(c.close - stop, 0.01)
    rr2 = max((targets[1] - c.close) / risk, 0.0)
    rr_score = 3 if rr2 >= 3 else 2 if rr2 >= 2 else 1 if rr2 >= 1.5 else 0
    vol_score = 2 if rvol >= 1.5 else 1 if rvol >= 1.0 else 0
    momentum = 1
    score = structure + level + vol_score + wyckoff + momentum + rr_score
    return {
        "kind": kind,
        "setup": setup,
        "signal_id": f"{TICKER}:{kind}:{c.end.isoformat()}",
        "price": c.close,
        "time": c.end.isoformat(),
        "entry": c.close,
        "stop": round(stop, 2),
        "tp1": targets[0], "tp2": targets[1], "tp3": targets[2],
        "rr_tp2": round(rr2, 2),
        "rvol": round(rvol, 2),
        "score": score,
        "score_note": "частичный Confluence Score /19: неиспользуемые факторы = 0",
    }


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(signal_id: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_signal_id": signal_id}, ensure_ascii=False), encoding="utf-8")


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Не заданы TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )
    r.raise_for_status()


def format_signal(s: dict[str, Any]) -> str:
    return (
        f"🚨 {TICKER} — READY\n\n"
        f"Setup: {s['setup']}\n"
        f"Цена: {s['price']:.2f} ₽\n"
        f"Время: {s['time']} MSK\n"
        f"RVOL: {s['rvol']}x\n\n"
        f"Entry: ~{s['entry']:.2f} ₽\nStop: {s['stop']:.2f} ₽\n"
        f"TP1: {s['tp1']:.2f} ₽\nTP2: {s['tp2']:.2f} ₽\nTP3: {s['tp3']:.2f} ₽\n"
        f"R/R до TP2: {s['rr_tp2']}\n"
        f"Confluence: {s['score']}/19 ({s['score_note']})\n\n"
        "Статус: READY\n"
        "⚠️ Проверь общий рынок и корпоративные события перед сделкой."
    )


def run() -> int:
    mode = os.getenv("MODE", "run")
    if mode == "test_telegram":
        send_telegram("✅ VKCO R1.0 Production: Telegram test OK")
        print("telegram_test=OK")
        return 0

    candles = fetch_candles()
    latest = candles[-1]
    now = datetime.now(MOSCOW)
    print(f"latest={latest.end.isoformat()} close={latest.close:.2f} volume={latest.volume:.0f}")

    # Не сигнализируем по старым данным (выходной/неактуальная сессия).
    if latest.end.date() != now.date() or now - latest.end > timedelta(minutes=45):
        print("status=WAIT reason=STALE_OR_MARKET_CLOSED")
        return 0

    signal = detect_signal(candles)
    if not signal:
        print("status=WAIT reason=NO_TRIGGER")
        return 0

    state = load_state()
    if state.get("last_signal_id") == signal["signal_id"]:
        print(f"status=WAIT reason=DUPLICATE signal_id={signal['signal_id']}")
        return 0

    send_telegram(format_signal(signal))
    save_state(signal["signal_id"])
    print(f"status=READY sent=1 signal_id={signal['signal_id']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
