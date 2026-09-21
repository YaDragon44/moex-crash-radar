from __future__ import annotations

import json
from pathlib import Path

from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.moex import fetch_index_history, fetch_share_history
from moex_crash_radar.transition_research import MODELS, summarize_model
from run_historical_evidence import load_constituents

START = "2019-03-22"
END = "2026-09-18"
DEVELOPMENT_END = "2023-12-29"
HOLDOUT_START = "2024-01-01"

def main() -> None:
    constituents = load_constituents()
    secids = sorted({secid for basket in constituents.values() for secid in basket})
    index = fetch_index_history("IMOEX", start=START, end=END)
    if len(index) < 200:
        raise SystemExit(f"insufficient IMOEX history: {len(index)}")
    universe, failures = {}, {}
    for secid in secids:
        try:
            candles = fetch_share_history(secid, start=START, end=END)
            if candles:
                universe[secid] = candles
            else:
                failures[secid] = "no candles"
        except Exception as exc:
            failures[secid] = f"{type(exc).__name__}: {exc}"
    rows = build_daily_evidence(index, universe, min_equity_coverage=0.70, warmup=60, universe_by_effective_date=constituents)
    if not rows:
        raise SystemExit("no daily evidence generated")
    development = {model: summarize_model(rows, model, start=START, end=DEVELOPMENT_END) for model in MODELS}
    holdout = {model: summarize_model(rows, model, start=HOLDOUT_START, end=END) for model in MODELS}
    payload = {
        "release": "R1.5.3-B locked public historical replay", "status": "INCONCLUSIVE", "production": "NO-GO",
        "reason": "First preregistered replay reports empirical evidence only; no production threshold or projection authorization exists.",
        "source": {"market_data": "MOEX ISS", "breadth_universe": "official IMOEX calculation-base archive", "period": {"start": START, "end": END}},
        "time_semantics": {"event_time": "daily candle trade date", "available_time": "next trading session 10:00 Europe/Moscow", "look_ahead_in_features": False, "outcome": "next 20 trading sessions minimum close <= -8%"},
        "quality": {"minimum_equity_coverage": 0.70, "index_rows": len(index), "evidence_rows": len(rows), "usable_secids": len(universe), "failed_secids": failures, "coverage_min": min(row.coverage for row in rows), "coverage_max": max(row.coverage for row in rows)},
        "models": {"development": development, "holdout": holdout},
        "incremental_m4_vs_m0_holdout": {key: (None if holdout["M4"][key] is None or holdout["M0"][key] is None else round(holdout["M4"][key] - holdout["M0"][key], 4)) for key in ("precision", "recall", "false_alarm_rate")},
        "locks": {"no_score_change": True, "no_exit_gate_change": True, "no_action_change": True, "no_ui_change": True},
    }
    out = Path("artifacts/r1_5_3b_transition_replay.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
