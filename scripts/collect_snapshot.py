from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from moex_crash_radar.breadth import breadth_signal, calculate_breadth, index_vs_breadth_divergence
from moex_crash_radar.distribution import calculate_distribution, distribution_signal
from moex_crash_radar.engine import calculate_crash, crash_momentum
from moex_crash_radar.features import derive_index_signals
from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.live_gate import CALIBRATED_EXIT_GATE, exit_gate_status
from moex_crash_radar.moex import fetch_index_candles, fetch_share_candles


BREADTH_UNIVERSE = (
    "SBER", "SBERP", "LKOH", "GAZP", "YDEX", "T", "X5", "GMKN",
    "NVTK", "ROSN", "TATN", "TATNP", "PLZL", "CHMF", "NLMK", "ALRS",
    "MOEX", "MTSS", "PHOR", "IRAO", "HYDR", "AFLT", "VKCO", "OZON",
)


def main() -> None:
    end = date.today()
    start = end - timedelta(days=500)
    index_candles = fetch_index_candles("IMOEX", start=start.isoformat(), end=end.isoformat())
    if not index_candles:
        raise SystemExit("MOEX returned no IMOEX candles")

    signals = derive_index_signals(index_candles)
    universe = {}
    failed = []
    for secid in BREADTH_UNIVERSE:
        try:
            candles = fetch_share_candles(secid, start=start.isoformat(), end=end.isoformat())
            if len(candles) >= 51:
                universe[secid] = candles
            else:
                failed.append(secid)
        except Exception:
            failed.append(secid)

    breadth = calculate_breadth(universe)
    breadth_payload = None
    breadth_coverage = 0.0
    if breadth is not None:
        breadth_coverage = breadth.usable_size / len(BREADTH_UNIVERSE)
        breadth_payload = {
            "universe_size": len(BREADTH_UNIVERSE),
            "usable_size": breadth.usable_size,
            "coverage": round(breadth_coverage, 4),
            "pct_above_ma20": breadth.pct_above_ma20,
            "pct_above_ma50": breadth.pct_above_ma50,
            "pct_new_20d_lows": breadth.pct_new_20d_lows,
            "pct_new_20d_highs": breadth.pct_new_20d_highs,
            "advance_decline_ratio": breadth.advance_decline_ratio,
            "breadth_return_5d": breadth.breadth_return_5d,
            "index_vs_breadth_divergence": index_vs_breadth_divergence(index_candles, breadth),
            "failed_secids": failed,
        }
        if breadth.usable_size >= 12 and breadth_coverage >= 0.50:
            signals["breadth"] = breadth_signal(breadth)

    distribution = calculate_distribution(universe)
    distribution_payload = None
    if distribution is not None:
        distribution_payload = {
            "usable_size": distribution.usable_size,
            "pct_down_rvol": distribution.pct_down_rvol,
            "pct_distribution_5d": distribution.pct_distribution_5d,
            "mean_down_up_volume_ratio": distribution.mean_down_up_volume_ratio,
        }
        if distribution.usable_size >= 12 and breadth_coverage >= 0.50:
            signals["volume_distribution"] = distribution_signal(distribution)

    crash = calculate_crash(signals)
    evidence = build_daily_evidence(index_candles, universe, min_equity_coverage=0.50, warmup=60)
    exit_gate = exit_gate_status(evidence)
    score_history = [x.score for x in evidence if x.score is not None]
    momentum = crash_momentum(score_history, 5) if len(score_history) > 5 else None
    crash_history = [
        {"day": x.day, "score": x.score, "state": x.state}
        for x in evidence[-120:]
        if x.score is not None
    ]

    payload = {
        "release": "R0.4.3 Analytical UX Completion",
        "as_of": index_candles[-1].begin,
        "source": "MOEX ISS",
        "secid": "IMOEX",
        "last_close": index_candles[-1].close,
        "data_quality": crash.quality.value,
        "signals": {k: {"score": v.score, "quality": v.quality.value} for k, v in signals.items()},
        "breadth": breadth_payload,
        "volume_distribution": distribution_payload,
        "crash": {
            "score": crash.score,
            "state": crash.state.value,
            "available_weight": round(crash.available_weight, 4),
            "critical_confirmations": crash.critical_confirmations,
            "raw_cash_signal": crash.cash_signal,
        },
        "exit_gate": exit_gate,
        "crash_momentum": momentum,
        "crash_history": crash_history,
        "bottom": {
            "score": None,
            "state": "DATA_INSUFFICIENT",
            "buy_back_signal": False,
        },
        "calibration": {
            "release": "R0.3.3",
            "false_event_rate": 0.2857,
            "detected_episodes": "4/4",
            "median_lead_days": 28.5,
            "total_exit_events": 14,
            "false_exit_events": 4,
            "params": {
                "score_threshold": CALIBRATED_EXIT_GATE.score_threshold,
                "confirmations": CALIBRATED_EXIT_GATE.confirmations,
                "persistence": CALIBRATED_EXIT_GATE.persistence,
                "max_5d_return_pct": CALIBRATED_EXIT_GATE.max_5d_return_pct,
                "cooldown_rows": CALIBRATED_EXIT_GATE.cooldown_rows,
                "rearm_clear_rows": CALIBRATED_EXIT_GATE.rearm_clear_rows,
            },
            "warning": "Calibration evidence uses a present-day liquid basket; historical breadth has survivorship/listing-history bias.",
        },
        "note": "Live MOEX market layer is active. Macro/news groups and Bottom Engine inputs are intentionally N/A until sourced; missing data is never invented.",
    }

    out = Path("artifacts/market_snapshot.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
