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


def _candles_url(secid: str, market: str, board: str | None = None) -> str:
    base = f"https://iss.moex.com/iss/engines/stock/markets/{market}"
    if board:
        return f"{base}/boards/{board}/securities/{secid}/candles.json"
    return f"{base}/securities/{secid}/candles.json"


def fetch_candles(secid: str = TICKER, market: str = "shares", board: str | None = BOARD,
                  days: int = 7) -> list[Candle]:
    date_from = (datetime.now(MOSCOW) - timedelta(days=days)).date().isoformat()
    rows: list[list[Any]] = []
    columns: list[str] | None = None
    offset = 0
    url = _candles_url(secid, market, board)

    while True:
        r = requests.get(
            url,
            params={"interval": INTERVAL, "from": date_from, "start": offset, "iss.meta": "off"},
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
            raise RuntimeError(f"Слишком много страниц MOEX candles: {secid}")

    if columns is None:
        raise RuntimeError(f"MOEX не вернул структуру candles: {secid}")

    out: list[Candle] = []
    now = datetime.now(MOSCOW)
    for row in rows:
        item = dict(zip(columns, row))
        c = Candle(
            begin=_dt(item["begin"]), end=_dt(item["end"]),
            open=float(item["open"]), close=float(item["close"]),
            high=float(item["high"]), low=float(item["low"]),
            volume=float(item.get("volume") or 0),
        )
        if c.end <= now:
            out.append(c)

    if len(out) < 25:
        raise RuntimeError(f"Недостаточно завершенных свечей MOEX {secid}: {len(out)}")
    return out


def adaptive_levels(candles: list[Candle], lookback: int = 20) -> dict[str, float]:
    if len(candles) < lookback + 3:
        raise ValueError("Недостаточно свечей для adaptive levels")
    ref = candles[-(lookback + 3):-3]
    return {
        "support": min(x.low for x in ref),
        "resistance": max(x.high for x in ref),
        "avg_range": mean(max(x.high - x.low, 0.01) for x in ref),
        "avg_volume": mean(x.volume for x in ref) or 1.0,
    }


def detect_signal(candles: list[Candle]) -> dict[str, Any] | None:
    a, b, c = candles[-3], candles[-2], candles[-1]
    lv = adaptive_levels(candles)
    support, resistance = lv["support"], lv["resistance"]
    avg_range, avg_volume = lv["avg_range"], lv["avg_volume"]
    rvol_b = b.volume / avg_volume
    rvol_c = c.volume / avg_volume

    # Adaptive breakout: пробой максимума предыдущих 20 свечей,
    # два закрытия выше уровня + объем на пробойной свече.
    if a.close <= resistance and b.close > resistance and c.close > resistance and rvol_b >= 1.20:
        stop = resistance - max(avg_range * 0.60, 0.30)
        risk = max(c.close - stop, 0.01)
        targets = (c.close + 1.5 * risk, c.close + 2.5 * risk, c.close + 4.0 * risk)
        return _signal(
            "ADAPTIVE_BREAKOUT", "Adaptive Breakout + Hold", c, max(rvol_b, rvol_c),
            stop=stop, targets=targets, structure=2, level=2, wyckoff=0,
            support=support, resistance=resistance,
        )

    # Adaptive spring: прокол минимума предыдущих 20 свечей, возврат выше уровня,
    # подтверждение следующей свечой + повышенный объем на spring-свече.
    if b.low < support and b.close > support and c.low >= support and c.close >= b.close and rvol_b >= 1.30:
        stop = b.low - max(avg_range * 0.25, 0.20)
        risk = max(c.close - stop, 0.01)
        tp1 = max(resistance, c.close + 1.5 * risk)
        targets = (tp1, c.close + 2.5 * risk, c.close + 4.0 * risk)
        return _signal(
            "ADAPTIVE_SPRING", "Adaptive Wyckoff Spring", c, max(rvol_b, rvol_c),
            stop=stop, targets=targets, structure=2, level=2, wyckoff=1,
            support=support, resistance=resistance,
        )
    return None


def market_filter(index_candles: list[Candle]) -> dict[str, Any]:
    if len(index_candles) < 21:
        raise ValueError("Недостаточно свечей IMOEX для market filter")
    latest = index_candles[-1]
    sma20 = mean(x.close for x in index_candles[-20:])
    one_hour_base = index_candles[-7].close
    one_hour_return = (latest.close / one_hour_base - 1.0) * 100 if one_hour_base else 0.0
    ok = latest.close >= sma20 * 0.995 and one_hour_return >= -0.70
    score = 2 if latest.close >= sma20 and one_hour_return >= 0 else 1 if ok else 0
    return {
        "ok": ok,
        "score": score,
        "close": latest.close,
        "sma20": sma20,
        "return_1h_pct": one_hour_return,
        "time": latest.end.isoformat(),
    }


def apply_market_filter(signal: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
    signal = dict(signal)
    signal["market"] = market
    signal["score"] += market["score"]
    return signal


def _signal(kind: str, setup: str, c: Candle, rvol: float, stop: float,
            targets: tuple[float, float, float], structure: int, level: int, wyckoff: int,
            support: float, resistance: float) -> dict[str, Any]:
    risk = max(c.close - stop, 0.01)
    rr2 = max((targets[1] - c.close) / risk, 0.0)
    rr_score = 3 if rr2 >= 3 else 2 if rr2 >= 2 else 1 if rr2 >= 1.5 else 0
    vol_score = 2 if rvol >= 1.5 else 1 if rvol >= 1.0 else 0
    score = structure + level + vol_score + wyckoff + 1 + rr_score
    return {
        "kind": kind, "setup": setup,
        "signal_id": f"{TICKER}:{kind}:{c.end.isoformat()}",
        "price": c.close, "time": c.end.isoformat(), "entry": c.close,
        "stop": round(stop, 2),
        "tp1": round(targets[0], 2), "tp2": round(targets[1], 2), "tp3": round(targets[2], 2),
        "rr_tp2": round(rr2, 2), "rvol": round(rvol, 2), "score": score,
        "support": round(support, 2), "resistance": round(resistance, 2),
        "score_note": "Confluence /19: структура, уровень, объем, Wyckoff, momentum, R/R, рынок",
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
        json={"chat_id": chat_id, "text": text}, timeout=20,
    )
    r.raise_for_status()


def format_signal(s: dict[str, Any]) -> str:
    m = s["market"]
    return (
        f"🚨 {TICKER} — READY\n\n"
        f"Setup: {s['setup']}\nЦена: {s['price']:.2f} ₽\nВремя: {s['time']} MSK\n"
        f"Adaptive support/resistance: {s['support']:.2f} / {s['resistance']:.2f} ₽\n"
        f"RVOL: {s['rvol']}x\nIMOEX: {m['close']:.2f}; 1ч {m['return_1h_pct']:+.2f}%\n\n"
        f"Entry: ~{s['entry']:.2f} ₽\nStop: {s['stop']:.2f} ₽\n"
        f"TP1: {s['tp1']:.2f} ₽\nTP2: {s['tp2']:.2f} ₽\nTP3: {s['tp3']:.2f} ₽\n"
        f"R/R до TP2: {s['rr_tp2']}\nConfluence: {s['score']}/19\n\n"
        "Статус: READY\n"
        "⚠️ Event Risk проверяй отдельно перед сделкой."
    )


def run() -> int:
    mode = os.getenv("MODE", "run")
    if mode == "test_telegram":
        send_telegram("✅ VKCO R1.2 Production: Telegram test OK")
        print("telegram_test=OK")
        return 0

    candles = fetch_candles()
    latest = candles[-1]
    now = datetime.now(MOSCOW)
    print(f"latest={latest.end.isoformat()} close={latest.close:.2f} volume={latest.volume:.0f}")

    if mode == "heartbeat":
        age_min = int((now - latest.end).total_seconds() // 60)
        send_telegram(
            f"💚 VKCO Monitor R1.2 — HEARTBEAT OK\n"
            f"MOEX latest: {latest.end.isoformat()} MSK\n"
            f"VKCO: {latest.close:.2f} ₽\nData age: {age_min} min"
        )
        print("heartbeat=OK")
        return 0

    if latest.end.date() != now.date() or now - latest.end > timedelta(minutes=45):
        print("status=WAIT reason=STALE_OR_MARKET_CLOSED")
        return 0

    signal = detect_signal(candles)
    if not signal:
        print("status=WAIT reason=NO_TRIGGER")
        return 0

    imoex = fetch_candles(secid="IMOEX", market="index", board=None, days=3)
    market = market_filter(imoex)
    print(
        f"imoex={market['close']:.2f} sma20={market['sma20']:.2f} "
        f"return_1h={market['return_1h_pct']:+.2f}% market_ok={market['ok']}"
    )
    if not market["ok"]:
        print("status=WAIT reason=MARKET_FILTER")
        return 0

    signal = apply_market_filter(signal, market)
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
