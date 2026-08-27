from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from moex_crash_radar.calibration import calibrate_cash_gate, signal_event_indices
from moex_crash_radar.history import build_daily_evidence, count_false_positive_days, evaluate_episode
from moex_crash_radar.moex import fetch_index_history, fetch_share_history


UNIVERSE = (
    "SBER", "SBERP", "LKOH", "GAZP", "YDEX", "T", "X5", "GMKN",
    "NVTK", "ROSN", "TATN", "TATNP", "PLZL", "CHMF", "NLMK", "ALRS",
    "MOEX", "MTSS", "PHOR", "IRAO", "HYDR", "AFLT", "VKCO", "OZON",
)

EPISODES = (
    ("COVID_2020", "2020-01-10", "2020-05-15"),
    ("FEB_2022", "2022-01-10", "2022-05-31"),
    ("SEP_2022", "2022-08-01", "2022-11-30"),
    ("CORRECTION_2024", "2024-05-01", "2024-09-30"),
    ("MARKET_2025_2026", "2025-01-01", "2026-08-27"),
)
CALIBRATION_EPISODES = EPISODES[:4]


def event_diagnostics(evidence, preferred):
    if not preferred:
        return []
    events = signal_event_indices(
        evidence,
        score_threshold=preferred["score_threshold"],
        confirmations=preferred["confirmations"],
        persistence=preferred["persistence"],
        max_5d_return_pct=preferred["max_5d_return_pct"],
        cooldown_rows=preferred["cooldown_rows"],
        require_breadth_volume=preferred["require_breadth_volume"],
        rearm_clear_rows=preferred["rearm_clear_rows"],
    )
    out = []
    for i in events:
        future = evidence[i : i + 21]
        if len(future) < 21:
            continue
        base = evidence[i].close
        min_close = min(x.close for x in future)
        dd = (min_close / base - 1.0) * 100.0
        row = evidence[i]
        out.append(
            {
                "day": row.day,
                "close": row.close,
                "score": row.score,
                "critical_confirmations": row.critical_confirmations,
                "breadth_score": row.breadth_score,
                "volume_distribution_score": row.volume_distribution_score,
                "forward_20row_min_drawdown_pct": round(dd, 2),
                "false_event": dd > -8.0,
            }
        )
    return out


def main() -> None:
    start = "2019-09-01"
    end = "2026-08-27"
    index = fetch_index_history("IMOEX", start=start, end=end)
    if len(index) < 200:
        raise SystemExit(f"insufficient IMOEX history: {len(index)}")

    universe = {}
    failures: dict[str, str] = {}
    for secid in UNIVERSE:
        try:
            candles = fetch_share_history(secid, start=start, end=end)
            if len(candles) >= 60:
                universe[secid] = candles
            else:
                failures[secid] = f"only {len(candles)} candles"
        except Exception as exc:
            failures[secid] = f"{type(exc).__name__}: {exc}"

    evidence = build_daily_evidence(index, universe, min_equity_coverage=0.50, warmup=60)
    if not evidence:
        raise SystemExit("no daily evidence generated")

    episodes = []
    for name, ep_start, ep_end in EPISODES:
        try:
            episodes.append(asdict(evaluate_episode(evidence, name=name, start=ep_start, end=ep_end)))
        except ValueError:
            episodes.append({"name": name, "status": "NO_DATA"})

    cash_days, false_cash_days = count_false_positive_days(evidence)
    candidates = calibrate_cash_gate(evidence, CALIBRATION_EPISODES)
    calibration = [asdict(x) for x in candidates]
    preferred = calibration[0] if calibration else None
    diagnostics = event_diagnostics(evidence, preferred)

    scored = [x for x in evidence if x.score is not None]
    coverage_values = [x.coverage for x in evidence]

    gate_pass = bool(
        preferred
        and preferred["detected_episodes"] == preferred["total_episodes"]
        and preferred["false_event_rate"] is not None
        and preferred["false_event_rate"] <= 0.35
        and preferred["median_lead_days"] is not None
        and preferred["median_lead_days"] >= 5
    )

    payload = {
        "release": "R0.3.3 Regime Rearm Precision Gate",
        "source": "MOEX ISS",
        "range": {"start": start, "end": end},
        "index_rows": len(index),
        "configured_universe": list(UNIVERSE),
        "usable_universe": sorted(universe),
        "failed_universe": failures,
        "methodology": {
            "point_in_time_features": True,
            "look_ahead": False,
            "min_breadth_coverage": 0.50,
            "score_data_gate": 0.70,
            "state_machine": "EARLY_WARNING -> EXIT_WATCH -> CASH_CONFIRMED -> DISARMED -> REARMED",
            "cash_confirmed_inputs": "Crash Score + critical confirmations + persistence + optional 5D downside + optional breadth/volume confirmation + cooldown + clear-regime rearm hysteresis",
            "calibration_false_positive_definition": "Independent CASH_CONFIRMED event not followed by <= -8% decline within next 20 evidence rows",
            "calibration_episodes": [x[0] for x in CALIBRATION_EPISODES],
            "excluded_from_threshold_fit": ["MARKET_2025_2026: broad regime window, not a clean crash episode"],
            "warning": "Breadth uses a present-day liquid basket, not historical index constituents. 2020/2022 results have survivorship/listing-history bias and remain calibration evidence, not unbiased production performance.",
        },
        "evidence_rows": len(evidence),
        "scored_rows": len(scored),
        "scored_share": round(len(scored) / len(evidence), 4),
        "coverage": {
            "min": round(min(coverage_values), 4),
            "max": round(max(coverage_values), 4),
            "last": round(coverage_values[-1], 4),
        },
        "episodes": episodes,
        "legacy_false_positive_days": {
            "cash_days_with_full_horizon": cash_days,
            "false_cash_days": false_cash_days,
            "rate": round(false_cash_days / cash_days, 4) if cash_days else None,
            "release_gate_metric": False,
        },
        "calibration": {
            "preferred_candidate": preferred,
            "top_candidates": calibration[:15],
            "preferred_event_diagnostics": diagnostics,
            "release_gate": {
                "pass": gate_pass,
                "requirements": "detect all four clean calibration episodes; false_event_rate <= 35%; median lead >= 5 calendar days",
            },
        },
        "latest": asdict(evidence[-1]),
    }

    out = Path("artifacts/historical_evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
