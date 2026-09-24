from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import monitor
from decision_audit import append_if_changed
from position_manager import has_active_position, load_state_file
from trade_journal import load_records, stats
from yandex_consensus import fetch_consensus
import strategy2_ema

OUTPUT = Path(os.getenv("PUBLIC_STATUS_FILE", "vkco-monitor/state/public_status.json"))
JOURNAL_JSONL = Path(os.getenv("JOURNAL_JSONL", "vkco-monitor/state/trade_journal.jsonl"))
ACTIVE = {"OPEN", "TP1", "TP2", "TRAILING"}
PUBLIC_CANDLES_LIMIT = 72


def _safe_position(state: dict[str, Any]) -> dict[str, Any] | None:
    p = state.get("position") if isinstance(state, dict) else None
    if not isinstance(p, dict):
        return None
    keys = (
        "ticker", "direction", "status", "signal_id", "opened_at", "entry", "stop",
        "tp1", "tp2", "tp3", "shares", "lots", "initial_risk_rub", "setup", "score",
        "last_event", "last_price",
    )
    return {k: p.get(k) for k in keys if k in p}


def _public_candles(candles: list[monitor.Candle], limit: int = PUBLIC_CANDLES_LIMIT) -> list[dict[str, Any]]:
    """Return a small, secret-free browser contract for the VKCO M10 chart."""
    return [
        {
            "t": c.begin.isoformat(),
            "end": c.end.isoformat(),
            "o": c.open,
            "h": c.high,
            "l": c.low,
            "c": c.close,
            "v": c.volume,
        }
        for c in candles[-limit:]
    ]


def build_status() -> dict[str, Any]:
    now = datetime.now(monitor.MOSCOW)
    state = load_state_file(monitor.STATE_FILE)
    records = load_records(JOURNAL_JSONL)
    journal = stats(records)

    payload: dict[str, Any] = {
        "schema_version": 2,
        "release": "R1.8",
        "dashboard_release": "R0.6.2",
        "generated_at": now.isoformat(),
        "ticker": monitor.TICKER,
        "mode": os.getenv("MODE", "run"),
        "health": "OK",
        "trade": {"status": "WAIT", "reason": "NO_DATA"},
        "position": _safe_position(state),
        "journal": journal,
        "analyst_consensus": fetch_consensus(),
        "entry_log": [
            {k: r.get(k) for k in ("signal_id", "opened_at", "closed_at", "status", "entry", "exit", "result_r", "setup", "score", "reason")}
            for r in records[-20:]
            if r.get("opened_at") and r.get("setup")
        ],
        "risk": {
            "capital_rub": float(os.getenv("TRADING_CAPITAL_RUB", "1000000") or 1000000),
            "risk_pct": float(os.getenv("RISK_PCT", "0.5") or 0.5),
        },
    }
    payload["risk"]["max_risk_rub"] = round(
        payload["risk"]["capital_rub"] * payload["risk"]["risk_pct"] / 100.0, 2
    )

    candles = monitor.fetch_candles()
    payload["candles"] = _public_candles(candles)
    try:
        payload["strategy2"] = strategy2_ema.public_snapshot(candles)
    except Exception as exc:
        payload["strategy2"] = {"strategy": "S2_EMA50_200_M10", "mode": "SHADOW", "status": "DATA_UNAVAILABLE", "error": type(exc).__name__}
    latest = candles[-1]
    age_min = int((now - latest.end).total_seconds() // 60)
    fresh = latest.end.date() == now.date() and now - latest.end <= monitor.timedelta(minutes=45)
    levels = monitor.adaptive_levels(candles)
    payload["market"] = {
        "price": latest.close,
        "candle_end": latest.end.isoformat(),
        "volume": latest.volume,
        "age_min": age_min,
        "fresh": fresh,
        "support": round(levels["support"], 2),
        "resistance": round(levels["resistance"], 2),
        "avg_range": round(levels["avg_range"], 4),
    }

    if has_active_position(state):
        p = state["position"]
        payload["trade"] = {
            "status": p.get("status", "OPEN"),
            "reason": p.get("last_event") or "MODEL_POSITION_ACTIVE",
            "setup": p.get("setup"),
            "score": p.get("score"),
        }
        return payload

    if not fresh:
        payload["trade"] = {"status": "WAIT", "reason": "STALE_OR_MARKET_CLOSED"}
        return payload

    signal = monitor.detect_signal(candles)
    if not signal:
        payload["trade"] = {"status": "WAIT", "reason": "NO_TRIGGER"}
        return payload

    imoex = monitor.fetch_candles(secid="IMOEX", market="index", board=None, days=3)
    market_filter = monitor.market_filter(imoex)
    signal = monitor.apply_market_filter(signal, market_filter)
    payload["imoex"] = market_filter
    payload["trade"] = {
        "status": "WAIT",
        "reason": "MARKET_FILTER" if not market_filter["ok"] else "CHECK_EVENT_RISK",
        "setup": signal.get("setup"),
        "score": signal.get("score"),
        "entry": signal.get("entry"),
        "stop": signal.get("stop"),
        "tp1": signal.get("tp1"),
        "tp2": signal.get("tp2"),
        "tp3": signal.get("tp3"),
        "rr_tp2": signal.get("rr_tp2"),
        "rvol": signal.get("rvol"),
        "support": signal.get("support"),
        "resistance": signal.get("resistance"),
        "signal_id": signal.get("signal_id"),
    }
    if not market_filter["ok"]:
        return payload

    try:
        event_risk = monitor.fetch_event_risk(now=now, window_days=3)
    except Exception as exc:
        payload["trade"]["reason"] = "EVENT_DATA_UNAVAILABLE"
        payload["event_risk"] = {"ok": False, "error": type(exc).__name__}
        return payload

    payload["event_risk"] = {
        "ok": event_risk.get("ok", False),
        "window_days": event_risk.get("window_days"),
        "source": event_risk.get("source"),
        "items": event_risk.get("items", [])[:3],
    }
    if not event_risk["ok"]:
        payload["trade"]["reason"] = "EVENT_RISK"
        return payload

    if state.get("last_signal_id") == signal["signal_id"]:
        payload["trade"]["reason"] = "DUPLICATE"
        return payload

    payload["trade"]["status"] = "READY"
    payload["trade"]["reason"] = "TRIGGER_CONFIRMED"
    return payload


def _audit_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    trade = payload.get("trade") or {}
    market = payload.get("market") or {}
    imoex = payload.get("imoex") or {}
    event = payload.get("event_risk")
    return {
        "timestamp": payload.get("generated_at"),
        "candle": market.get("candle_end"),
        "status": trade.get("status"),
        "reason": trade.get("reason"),
        "setup": trade.get("setup"),
        "support": trade.get("support", market.get("support")),
        "resistance": trade.get("resistance", market.get("resistance")),
        "rvol": trade.get("rvol"),
        "trigger": trade.get("reason") not in {"NO_TRIGGER", "STALE_OR_MARKET_CLOSED", "NO_DATA"},
        "imoex": {
            "ok": imoex.get("ok"),
            "close": imoex.get("close"),
            "sma20": imoex.get("sma20"),
            "return_1h_pct": imoex.get("return_1h_pct"),
        } if imoex else None,
        "event_risk": {
            "ok": event.get("ok"),
            "window_days": event.get("window_days"),
            "error": event.get("error"),
        } if isinstance(event, dict) else None,
        "score": trade.get("score"),
        "entry": trade.get("entry"),
        "stop": trade.get("stop"),
        "tp1": trade.get("tp1"),
        "tp2": trade.get("tp2"),
        "tp3": trade.get("tp3"),
        "signal_id": trade.get("signal_id"),
    }


def export_status(path: Path = OUTPUT) -> dict[str, Any]:
    try:
        payload = build_status()
    except Exception as exc:
        now = datetime.now(monitor.MOSCOW)
        payload = {
            "schema_version": 2,
            "release": "R1.8",
            "dashboard_release": "R0.6.2",
            "generated_at": now.isoformat(),
            "ticker": monitor.TICKER,
            "health": "DEGRADED",
            "trade": {"status": "WAIT", "reason": "STATUS_EXPORT_ERROR"},
            "candles": [],
            "error": type(exc).__name__,
        }
    # Evidence-only side effect: persist the evaluated decision after the complete
    # production pipeline has built it. This does not feed back into signal logic.
    append_if_changed(_audit_snapshot(payload))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = export_status()
    print(
        f"public_status={result.get('health')} trade_status={result.get('trade', {}).get('status')} "
        f"reason={result.get('trade', {}).get('reason')} candles={len(result.get('candles') or [])}"
    )
