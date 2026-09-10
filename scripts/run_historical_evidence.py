from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from statistics import median

from moex_crash_radar.calibration import signal_event_indices
from moex_crash_radar.history import build_daily_evidence, count_false_positive_days, evaluate_episode
from moex_crash_radar.live_gate import CALIBRATED_EXIT_GATE
from moex_crash_radar.moex import fetch_index_history, fetch_share_history

CONSTITUENTS_FILE = Path("data/imoex_constituents_2019_2026.json")
OFFICIAL_CONSTITUENTS_SOURCE = "https://www.moex.com/ru/documents/15237"

EPISODES = (
    ("COVID_2020", "2020-01-10", "2020-05-15"),
    ("FEB_2022", "2022-01-10", "2022-05-31"),
    ("SEP_2022", "2022-08-01", "2022-11-30"),
    ("CORRECTION_2024", "2024-05-01", "2024-09-30"),
    ("MARKET_2025_2026", "2025-01-01", "2026-08-27"),
)
CALIBRATION_EPISODES = EPISODES[:4]


def load_constituents() -> dict[str, tuple[str, ...]]:
    payload = json.loads(CONSTITUENTS_FILE.read_text(encoding="utf-8"))
    bases = payload.get("bases") or {}
    if not bases:
        raise SystemExit("official IMOEX constituent bases are empty")
    return {day: tuple(codes) for day, codes in sorted(bases.items())}


def frozen_event_indices(evidence):
    p = CALIBRATED_EXIT_GATE
    return signal_event_indices(
        evidence,
        score_threshold=p.score_threshold,
        confirmations=p.confirmations,
        persistence=p.persistence,
        max_5d_return_pct=p.max_5d_return_pct,
        cooldown_rows=p.cooldown_rows,
        require_breadth_volume=p.require_breadth_volume,
        rearm_clear_rows=p.rearm_clear_rows,
    )


def event_diagnostics(evidence, events):
    out = []
    for i in events:
        future = evidence[i : i + 21]
        if len(future) < 21:
            continue
        row = evidence[i]
        min_close = min(x.close for x in future)
        dd = (min_close / row.close - 1.0) * 100.0
        out.append({
            "day": row.day,
            "close": row.close,
            "score": row.score,
            "critical_confirmations": row.critical_confirmations,
            "breadth_score": row.breadth_score,
            "volume_distribution_score": row.volume_distribution_score,
            "coverage": row.coverage,
            "forward_20row_min_drawdown_pct": round(dd, 2),
            "false_event": dd > -8.0,
        })
    return out


def episode_detection(evidence, events):
    event_days = [evidence[i].day for i in events]
    rows = []
    leads = []
    for name, start, end in CALIBRATION_EPISODES:
        episode = evaluate_episode(evidence, name=name, start=start, end=end)
        eligible = [d for d in event_days if start <= d <= episode.trough]
        first = eligible[0] if eligible else None
        lead = None
        if first:
            from datetime import date
            lead = (date.fromisoformat(episode.trough) - date.fromisoformat(first)).days
            leads.append(lead)
        rows.append({"name": name, "trough": episode.trough, "first_frozen_exit": first, "lead_days": lead, "detected": first is not None})
    return rows, leads


def main() -> None:
    start = "2019-09-01"
    end = "2026-08-27"
    constituents = load_constituents()
    all_secids = sorted({secid for basket in constituents.values() for secid in basket})

    index = fetch_index_history("IMOEX", start=start, end=end)
    if len(index) < 200:
        raise SystemExit(f"insufficient IMOEX history: {len(index)}")

    universe = {}
    failures: dict[str, str] = {}
    for secid in all_secids:
        try:
            candles = fetch_share_history(secid, start=start, end=end)
            if candles:
                universe[secid] = candles
            else:
                failures[secid] = "no candles"
        except Exception as exc:
            failures[secid] = f"{type(exc).__name__}: {exc}"

    evidence = build_daily_evidence(
        index,
        universe,
        min_equity_coverage=0.50,
        warmup=60,
        universe_by_effective_date=constituents,
    )
    if not evidence:
        raise SystemExit("no daily evidence generated")

    episodes = []
    for name, ep_start, ep_end in EPISODES:
        try:
            episodes.append(asdict(evaluate_episode(evidence, name=name, start=ep_start, end=ep_end)))
        except ValueError:
            episodes.append({"name": name, "status": "NO_DATA"})

    events = frozen_event_indices(evidence)
    diagnostics = event_diagnostics(evidence, events)
    clean_diagnostics = [x for x in diagnostics if x["day"] <= CALIBRATION_EPISODES[-1][2]]
    false_events = sum(1 for x in clean_diagnostics if x["false_event"])
    false_event_rate = false_events / len(clean_diagnostics) if clean_diagnostics else None
    detection, leads = episode_detection(evidence, events)
    detected = sum(1 for x in detection if x["detected"])
    median_lead = median(leads) if leads else None

    coverage_values = [x.coverage for x in evidence]
    coverage_ok_share = sum(1 for x in evidence if x.coverage >= 0.50) / len(evidence)
    integrity_pass = coverage_ok_share >= 0.90
    metric_gate_pass = bool(
        detected == len(CALIBRATION_EPISODES)
        and false_event_rate is not None and false_event_rate <= 0.35
        and median_lead is not None and median_lead >= 5
    )
    gate_pass = bool(integrity_pass and metric_gate_pass)
    status = "GO" if gate_pass else ("CONDITIONAL" if integrity_pass else "PARTIAL")

    cash_days, false_cash_days = count_false_positive_days(evidence)
    payload = {
        "release": "R0.6 Historical Integrity",
        "source": "MOEX ISS + official IMOEX calculation-base archive",
        "range": {"start": start, "end": end},
        "historical_integrity": {
            "status": status,
            "feature_timestamps_point_in_time": True,
            "universe_point_in_time": True,
            "constituent_bases": len(constituents),
            "constituent_union": len(all_secids),
            "source_ref": OFFICIAL_CONSTITUENTS_SOURCE,
            "coverage_ok_share": round(coverage_ok_share, 4),
            "integrity_gate_pass": integrity_pass,
            "release_gate_pass": gate_pass,
        },
        "methodology": {
            "look_ahead": False,
            "min_breadth_coverage": 0.50,
            "threshold_refit": False,
            "exit_gate": asdict(CALIBRATED_EXIT_GATE),
            "rule": "Frozen production Crash/EXIT logic is replayed unchanged on official point-in-time IMOEX constituents.",
        },
        "data": {
            "index_rows": len(index),
            "requested_secids": len(all_secids),
            "usable_secids": len(universe),
            "failed_secids": failures,
            "evidence_rows": len(evidence),
            "coverage": {"min": round(min(coverage_values), 4), "max": round(max(coverage_values), 4), "last": round(coverage_values[-1], 4)},
        },
        "episodes": episodes,
        "frozen_exit_validation": {
            "detected_episodes": detected,
            "total_episodes": len(CALIBRATION_EPISODES),
            "episode_detection": detection,
            "events_with_full_horizon": len(clean_diagnostics),
            "false_events": false_events,
            "false_event_rate": round(false_event_rate, 4) if false_event_rate is not None else None,
            "median_lead_days": median_lead,
            "metric_gate_pass": metric_gate_pass,
            "event_diagnostics": diagnostics,
        },
        "legacy_cash_day_metric": {
            "cash_days_with_full_horizon": cash_days,
            "false_cash_days": false_cash_days,
            "release_gate_metric": False,
        },
        "latest": asdict(evidence[-1]),
    }

    out = Path("artifacts/historical_evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
