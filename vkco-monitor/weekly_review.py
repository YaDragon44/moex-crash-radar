from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from trade_journal import load_records, stats

MOSCOW = ZoneInfo("Europe/Moscow")
JOURNAL_JSONL = Path(os.getenv("JOURNAL_JSONL", "vkco-monitor/state/trade_journal.jsonl"))


def weekly_records(records: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(MOSCOW)
    cutoff = now - timedelta(days=7)
    out: list[dict[str, Any]] = []
    for r in records:
        raw = r.get("closed_at")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MOSCOW)
            if dt >= cutoff:
                out.append(r)
        except Exception:
            continue
    return out


def _money(records: list[dict[str, Any]]) -> float:
    return round(sum(float(r.get("pnl_rub") or 0.0) for r in records), 2)


def _best_worst(records: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    usable = [r for r in records if r.get("result_r") is not None]
    if not usable:
        return None, None
    return max(usable, key=lambda r: float(r["result_r"])), min(usable, key=lambda r: float(r["result_r"]))


def _setup_summary(records: list[dict[str, Any]]) -> str:
    buckets: dict[str, list[float]] = {}
    for r in records:
        if r.get("result_r") is None:
            continue
        name = str(r.get("setup") or "UNKNOWN")
        buckets.setdefault(name, []).append(float(r["result_r"]))
    if not buckets:
        return "Сетапы: данных пока недостаточно."
    ranked = sorted(((sum(v) / len(v), k, len(v)) for k, v in buckets.items()), reverse=True)
    best = ranked[0]
    worst = ranked[-1]
    if best[1] == worst[1]:
        return f"Сетап: {best[1]} | {best[2]} сдел. | Avg {best[0]:+.2f}R"
    return f"Лучший сетап: {best[1]} {best[0]:+.2f}R | слабый: {worst[1]} {worst[0]:+.2f}R"


def build_weekly_review(records: list[dict[str, Any]], now: datetime | None = None) -> str:
    now = now or datetime.now(MOSCOW)
    week = weekly_records(records, now)
    all_stats = stats(records)
    week_stats = stats(week)

    if not week:
        return (
            "📊 VKCO — WEEKLY REVIEW\n\n"
            "За последние 7 дней завершённых модельных сделок нет.\n"
            f"Всего в журнале: {all_stats['trades']} сделок.\n"
            "ДЕЙСТВИЕ: статистику не переоценивать; ждём новый качественный READY."
        )

    pnl = _money(week)
    best, worst = _best_worst(week)
    pf = "∞" if week_stats["profit_factor"] is None and week_stats["wins"] > 0 else (
        f"{week_stats['profit_factor']:.2f}" if week_stats["profit_factor"] is not None else "n/a"
    )
    best_line = f"Лучшая: {float(best['result_r']):+.2f}R" if best else "Лучшая: n/a"
    worst_line = f"Худшая: {float(worst['result_r']):+.2f}R" if worst else "Худшая: n/a"
    expectancy = week_stats.get("expectancy_r")
    expectancy_text = f"{expectancy:+.3f}R" if expectancy is not None else "n/a"

    action = "сохранять правила без изменений"
    if expectancy is not None and expectancy < 0:
        action = "не повышать риск; разбирать причины отрицательного Expectancy"
    elif week_stats["trades"] < 3:
        action = "выборка мала; не менять систему по 1–2 сделкам"

    return (
        "📊 VKCO — WEEKLY REVIEW\n\n"
        f"Период: последние 7 дней\n"
        f"Сделки: {week_stats['trades']} | W/L: {week_stats['wins']}/{week_stats['losses']}\n"
        f"P/L: {pnl:+,.0f} ₽\n"
        f"Win Rate: {week_stats['win_rate']:.1f}%\n"
        f"Avg R: {week_stats['avg_r'] if week_stats['avg_r'] is not None else 'n/a'}\n"
        f"Profit Factor: {pf}\n"
        f"Expectancy: {expectancy_text}\n"
        f"{best_line} | {worst_line}\n"
        f"{_setup_summary(week)}\n\n"
        f"Всего в журнале: {all_stats['trades']} сделок.\n"
        f"ДЕЙСТВИЕ: {action}."
    )


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise RuntimeError("Не заданы TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text}, timeout=20,
    )
    r.raise_for_status()


def main() -> int:
    records = load_records(JOURNAL_JSONL)
    text = build_weekly_review(records)
    send_telegram(text)
    print(f"weekly_review=OK total_records={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
