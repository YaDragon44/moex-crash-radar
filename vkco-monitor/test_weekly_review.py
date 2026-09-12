from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from weekly_review import build_weekly_review, weekly_records

MSK = ZoneInfo("Europe/Moscow")


def rec(now, days_ago, pnl, result_r, setup="Breakout + Hold"):
    return {
        "status": "CLOSED_PROFIT" if pnl > 0 else "CLOSED_STOP",
        "closed_at": (now - timedelta(days=days_ago)).isoformat(),
        "pnl_rub": pnl,
        "result_r": result_r,
        "setup": setup,
    }


def test_weekly_records_filters_older_trades():
    now = datetime(2026, 9, 14, 8, 5, tzinfo=MSK)
    rows = [rec(now, 1, 5000, 1.0), rec(now, 9, -5000, -1.0)]
    week = weekly_records(rows, now)
    assert len(week) == 1
    assert week[0]["pnl_rub"] == 5000


def test_weekly_review_no_trades_is_compact():
    now = datetime(2026, 9, 14, 8, 5, tzinfo=MSK)
    text = build_weekly_review([], now)
    assert "завершённых модельных сделок нет" in text
    assert "ждём новый качественный READY" in text


def test_weekly_review_calculates_metrics():
    now = datetime(2026, 9, 14, 8, 5, tzinfo=MSK)
    rows = [
        rec(now, 1, 7500, 1.5, "Breakout + Hold"),
        rec(now, 2, -5000, -1.0, "Spring"),
    ]
    text = build_weekly_review(rows, now)
    assert "Сделки: 2 | W/L: 1/1" in text
    assert "P/L: +2,500 ₽" in text
    assert "Win Rate: 50.0%" in text
    assert "Expectancy: +0.250R" in text
    assert "выборка мала" in text


def test_negative_expectancy_blocks_risk_increase():
    now = datetime(2026, 9, 14, 8, 5, tzinfo=MSK)
    rows = [
        rec(now, 1, 2500, 0.5),
        rec(now, 2, -5000, -1.0),
        rec(now, 3, -5000, -1.0),
    ]
    text = build_weekly_review(rows, now)
    assert "не повышать риск" in text


def test_setup_summary_identifies_best_and_weak():
    now = datetime(2026, 9, 14, 8, 5, tzinfo=MSK)
    rows = [
        rec(now, 1, 7500, 1.5, "Breakout + Hold"),
        rec(now, 2, -5000, -1.0, "Spring"),
    ]
    text = build_weekly_review(rows, now)
    assert "Лучший сетап: Breakout + Hold" in text
    assert "слабый: Spring" in text
