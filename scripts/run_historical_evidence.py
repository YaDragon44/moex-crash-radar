from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from moex_crash_radar.calibration import calibrate_cash_gate
from moex_crash_radar.history import build_daily_evidence, count_false_positive_days, evaluate_episode
from moex_crash_radar.moex import fetch_index_history, fetch_share_history


# Current liquid basket. IMPORTANT: this is not a historical constituent set, so the
# 2020/2022 breadth backtest has survivorship/availability bias. The report exposes
# coverage and never silently substitutes missing tickers.
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
        except Exception as exc:  # source failures are evidence, not imputed data
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

    # Legacy day-level false-positive metric is retained for transparency, but it is
    # not the release Gate because one persistent risk regime can generate dozens of
    # CASH days. Calibration below evaluates independent signal events instead.
    cash_days, false_cash_days = count_false_positive_days(evidence)
    candidates = calibrate_cash_gate(evidence, EPISODES)
    calibration = [asdict(x) for x in candidates]
    preferred = calibration[0] if calibration else None

    scored = [x for x in evidence if x.score is not None]
    coverage_values = [x.coverage for x in evidence]

    # R0.3.1 Gate is intentionally conservative: all configured historical episodes
    # must be detected, event-level false positive rate <= 35%, and median lead >= 5d.
    gate_pass = bool(
        preferred
        and preferred["detected_episodes"] == preferred["total_episodes"]
        and preferred["false_event_rate"] is not None
        and preferred["false_event_rate"] <= 0.35
        and preferred["median_lead_days"] is not None
        and preferred["median_lead_days"] >= 5
    )

    payload = {
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
            "current_cash_gate": "Crash Score >=56 and >=3/4 critical market confirmations",
            "legacy_false_positive_definition": "CASH day not followed by <= -8% decline within next 20 evidence rows",
            "calibration_false_positive_definition": "Independent CASH event not followed by <= -8% decline within next 20 evidence rows",
            "warning": "Breadth uses a present-day liquid basket, not historical index constituents. 2020/2022 results therefore have survivorship and listing-history bias and must be treated as calibration evidence, not production-grade unbiased performance.",
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
            "top_candidates": calibration[:10],
            "release_gate": {
                "pass": gate_pass,
                "requirements": "detect all configured episodes; false_event_rate <= 35%; median lead >= 5 calendar days",
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
