from pathlib import Path

from trade_journal import append_record_once, build_record, load_records, stats


def position(**overrides):
    p = {
        "ticker": "VKCO",
        "direction": "LONG",
        "signal_id": "VKCO:TEST:1",
        "opened_at": "2026-09-14T10:00:00+03:00",
        "closed_at": "2026-09-14T12:00:00+03:00",
        "status": "CLOSED_PROFIT",
        "entry": 120.0,
        "exit_price": 128.0,
        "shares": 625,
        "initial_risk_rub": 5000.0,
        "setup": "Breakout + Hold",
        "score": 14,
        "last_event": "CLOSED_PROFIT",
    }
    p.update(overrides)
    return p


def test_build_record_calculates_pnl_and_r():
    r = build_record(position())
    assert r["pnl_rub"] == 5000.0
    assert r["result_r"] == 1.0
    assert r["setup"] == "Breakout + Hold"
    assert r["score"] == 14


def test_append_record_is_idempotent(tmp_path: Path):
    path = tmp_path / "journal.jsonl"
    _, added1 = append_record_once(path, position())
    _, added2 = append_record_once(path, position())
    assert added1 is True
    assert added2 is False
    assert len(load_records(path)) == 1


def test_stats_win_loss_expectancy():
    win = build_record(position())
    loss = build_record(position(
        signal_id="VKCO:TEST:2",
        closed_at="2026-09-15T12:00:00+03:00",
        status="CLOSED_STOP",
        exit_price=116.0,
        shares=1250,
        last_event="CLOSED_STOP",
    ))
    s = stats([win, loss])
    assert s["trades"] == 2
    assert s["wins"] == 1
    assert s["losses"] == 1
    assert s["win_rate"] == 50.0
    assert s["avg_r"] == 0.0
    assert s["profit_factor"] == 1.0
    assert s["expectancy_r"] == 0.0


def test_stats_empty_is_safe():
    s = stats([])
    assert s["trades"] == 0
    assert s["win_rate"] is None
