from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _journal_key(position: dict[str, Any]) -> str:
    return f"{position.get('signal_id')}|{position.get('closed_at')}|{position.get('status')}"


def build_record(position: dict[str, Any]) -> dict[str, Any]:
    entry = float(position["entry"])
    exit_price = float(position["exit_price"])
    shares = int(position.get("shares") or 0)
    initial_risk_rub = float(position.get("initial_risk_rub") or 0.0)
    pnl_per_share = exit_price - entry
    pnl_rub = pnl_per_share * shares if shares > 0 else 0.0
    result_r = pnl_rub / initial_risk_rub if initial_risk_rub > 0 else None
    return {
        "journal_key": _journal_key(position),
        "ticker": position.get("ticker", "VKCO"),
        "direction": position.get("direction", "LONG"),
        "signal_id": position.get("signal_id"),
        "opened_at": position.get("opened_at"),
        "closed_at": position.get("closed_at"),
        "status": position.get("status"),
        "entry": round(entry, 2),
        "exit": round(exit_price, 2),
        "shares": shares or None,
        "pnl_per_share": round(pnl_per_share, 2),
        "pnl_rub": round(pnl_rub, 2),
        "result_r": round(result_r, 3) if result_r is not None else None,
        "setup": position.get("setup"),
        "score": position.get("score"),
        "reason": position.get("last_event") or position.get("status"),
    }


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def append_record_once(path: Path, position: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    record = build_record(position)
    existing = load_records(path)
    if any(r.get("journal_key") == record["journal_key"] for r in existing):
        return record, False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record, True


def export_csv(jsonl_path: Path, csv_path: Path) -> None:
    rows = load_records(jsonl_path)
    if not rows:
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "ticker", "direction", "signal_id", "opened_at", "closed_at", "status",
        "entry", "exit", "shares", "pnl_per_share", "pnl_rub", "result_r",
        "setup", "score", "reason",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in records if r.get("status") in {"CLOSED_PROFIT", "CLOSED_STOP", "MANUAL_EXIT", "INVALIDATED"}]
    if not completed:
        return {"trades": 0, "wins": 0, "losses": 0, "win_rate": None, "avg_r": None, "profit_factor": None, "expectancy_r": None}

    rs = [float(r["result_r"]) for r in completed if r.get("result_r") is not None]
    wins = [r for r in completed if float(r.get("pnl_rub") or 0) > 0]
    losses = [r for r in completed if float(r.get("pnl_rub") or 0) < 0]
    gross_profit = sum(float(r.get("pnl_rub") or 0) for r in wins)
    gross_loss_abs = abs(sum(float(r.get("pnl_rub") or 0) for r in losses))
    win_rate = len(wins) / len(completed)
    avg_r = sum(rs) / len(rs) if rs else None
    avg_win_r = sum(float(r["result_r"]) for r in wins if r.get("result_r") is not None) / len(wins) if wins else 0.0
    avg_loss_r = abs(sum(float(r["result_r"]) for r in losses if r.get("result_r") is not None) / len(losses)) if losses else 0.0
    expectancy_r = win_rate * avg_win_r - (1 - win_rate) * avg_loss_r
    return {
        "trades": len(completed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate * 100, 1),
        "avg_r": round(avg_r, 3) if avg_r is not None else None,
        "profit_factor": round(gross_profit / gross_loss_abs, 2) if gross_loss_abs > 0 else None,
        "expectancy_r": round(expectancy_r, 3),
    }


def format_stats(s: dict[str, Any]) -> str:
    if s["trades"] == 0:
        return "Journal: пока нет завершённых модельных сделок."
    pf = "∞" if s["profit_factor"] is None and s["wins"] > 0 else (f"{s['profit_factor']:.2f}" if s["profit_factor"] is not None else "n/a")
    return (
        f"Journal: {s['trades']} сделок | Win Rate {s['win_rate']:.1f}% | "
        f"Avg R {s['avg_r'] if s['avg_r'] is not None else 'n/a'} | PF {pf} | "
        f"Expectancy {s['expectancy_r']:+.3f}R"
    )
