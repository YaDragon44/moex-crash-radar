from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from moex_crash_radar.calibration import calibrate_cash_gate
from moex_crash_radar.context_validation import (
    fetch_cnyrub_history,
    fetch_key_rate_history,
    fetch_rgbi_history,
    historical_context_points,
    validate_context_gate,
)
from moex_crash_radar.historical_oil import fetch_fred_brent_history
from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.moex import fetch_index_history, fetch_share_history


UNIVERSE = (
    "SBER", "SBERP", "LKOH", "GAZP", "YDEX", "T", "X5", "GMKN",
    "NVTK", "ROSN", "TATN", "TATNP", "PLZL", "CHMF", "NLMK", "ALRS",
    "MOEX", "MTSS", "PHOR", "IRAO", "HYDR", "AFLT", "VKCO", "OZON",
)

CALIBRATION_EPISODES = (
    ("COVID_2020", "2020-01-10", "2020-05-15"),
    ("FEB_2022", "2022-01-10", "2022-05-31"),
    ("SEP_2022", "2022-08-01", "2022-11-30"),
    ("CORRECTION_2024", "2024-05-01", "2024-09-30"),
)

MIN_CONTEXT_SCORED_SHARE = 0.60
MIN_BRENT_ROWS = 500


def main() -> None:
    start = "2019-09-01"
    end = "2026-08-27"

    index = fetch_index_history("IMOEX", start=start, end=end)
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
        raise SystemExit("no crash evidence")

    calibration = [asdict(x) for x in calibrate_cash_gate(evidence, CALIBRATION_EPISODES)]
    if not calibration:
        raise SystemExit("no calibrated EXIT candidate")
    preferred = calibration[0]

    key_rates = fetch_key_rate_history(start=start, end=end)
    rgbi = fetch_rgbi_history(start=start, end=end)
    brent = fetch_fred_brent_history(start=start, end=end)
    cnyrub = fetch_cnyrub_history(start=start, end=end)

    context = historical_context_points(
        evidence,
        key_rates=key_rates,
        rgbi=rgbi,
        brent=brent,
        cnyrub=cnyrub,
    )
    candidates = validate_context_gate(
        evidence,
        context,
        preferred=preferred,
        episodes=CALIBRATION_EPISODES,
    )

    scored_context = [x for x in context if x.score is not None]
    scored_share = round(len(scored_context) / len(context), 4) if context else 0.0
    data_gate_pass = bool(
        len(brent) >= MIN_BRENT_ROWS
        and len(key_rates) > 0
        and len(rgbi) > 0
        and len(cnyrub) > 0
        and scored_share >= MIN_CONTEXT_SCORED_SHARE
    )

    base_false_rate = preferred.get("false_event_rate")
    usable = [x for x in candidates if x.detected_episodes == len(CALIBRATION_EPISODES) and x.false_event_rate is not None]
    improved = [x for x in usable if base_false_rate is not None and x.false_event_rate < base_false_rate]
    best = min(improved, key=lambda x: (x.false_event_rate, -float(x.median_lead_days or 0))) if improved else None

    if not data_gate_pass:
        status = "DATA_GATE_FAIL_NO_DECISION"
        best = None
    elif best:
        status = "GO_FOR_RISK_INTEGRATION_REVIEW"
    else:
        status = "NO_GO_KEEP_CONTEXT_INFORMATIONAL"

    payload = {
        "release": "R0.5.3.1 Historical Oil Data Source Hotfix",
        "status": status,
        "source": "MOEX ISS + CBR + FRED/EIA",
        "range": {"start": start, "end": end},
        "methodology": {
            "point_in_time": True,
            "look_ahead": False,
            "context_changes_existing_exit_events_only": True,
            "live_exit_gate_unchanged": True,
            "historical_rate_ofz_proxy": "CBR key rate + RGBI 5D/20D; historical cross-sectional median OFZ yield unavailable, weights re-normalized",
            "historical_oil_rub_proxy": "FRED DCOILBRENTEU daily Europe Brent spot (underlying EIA series) + MOEX CNYRUB_TOM 5D/20D",
            "live_oil_source_unchanged": "Live Oil/RUB continues to use MOEX Brent futures; FRED is historical-validation-only.",
            "decision_rule": "Context may proceed to Risk Engine integration review only if a threshold reduces false-event rate while preserving detection of all four calibration episodes.",
            "warning": "Same present-day liquid equity universe limitation as R0.3.3 remains. This is calibration evidence, not unbiased production performance.",
        },
        "data_gate": {
            "pass": data_gate_pass,
            "min_brent_rows": MIN_BRENT_ROWS,
            "min_context_scored_share": MIN_CONTEXT_SCORED_SHARE,
        },
        "source_rows": {
            "imoex": len(index),
            "usable_equities": len(universe),
            "failed_equities": failures,
            "key_rate_points": len(key_rates),
            "rgbi": len(rgbi),
            "brent": len(brent),
            "cnyrub": len(cnyrub),
            "context_scored": len(scored_context),
            "context_total": len(context),
            "context_scored_share": scored_share,
        },
        "baseline_exit_gate": preferred,
        "context_candidates": [asdict(x) for x in candidates],
        "preferred_context_candidate": asdict(best) if best else None,
    }

    out = Path("artifacts/context_historical_validation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
