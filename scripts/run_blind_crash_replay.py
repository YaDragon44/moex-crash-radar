from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from statistics import median

from moex_crash_radar.calibration import signal_event_indices
from moex_crash_radar.history import build_daily_evidence, evaluate_episode
from moex_crash_radar.live_gate import CALIBRATED_EXIT_GATE
from moex_crash_radar.moex import fetch_index_history, fetch_share_history

CONSTITUENTS_FILE = Path("data/imoex_constituents_2019_2026.json")
OFFICIAL_CONSTITUENTS_SOURCE = "https://www.moex.com/ru/documents/15237"

# Holdout was not part of the four R0.6 calibration episodes.
BLIND_START = "2024-10-01"
BLIND_END = "2026-08-27"
FORWARD_ROWS = 20
CRASH_DRAWDOWN_PCT = -8.0


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


def main() -> None:
    # Keep pre-holdout warm-up data, but score only the blind interval.
    fetch_start = "2024-06-01"
    constituents = load_constituents()
    all_secids = sorted({s for basket in constituents.values() for s in basket})
    index = fetch_index_history("IMOEX", start=fetch_start, end=BLIND_END)
    universe = {}
    failures = {}
    for secid in all_secids:
        try:
            candles = fetch_share_history(secid, start=fetch_start, end=BLIND_END)
            if candles:
                universe[secid] = candles
            else:
                failures[secid] = "no candles"
        except Exception as exc:
            failures[secid] = f"{type(exc).__name__}: {exc}"

    evidence = build_daily_evidence(
        index, universe, min_equity_coverage=0.50, warmup=60,
        universe_by_effective_date=constituents,
    )
    blind = [x for x in evidence if BLIND_START <= x.day <= BLIND_END]
    if not blind:
        raise SystemExit("no blind evidence generated")

    events = frozen_event_indices(blind)
    diagnostics = []
    true_events = 0
    false_events = 0
    for i in events:
        future = blind[i:i + FORWARD_ROWS + 1]
        row = blind[i]
        if len(future) < FORWARD_ROWS + 1:
            diagnostics.append({"day": row.day, "status": "INCOMPLETE_FORWARD_HORIZON"})
            continue
        min_row = min(future, key=lambda x: x.close)
        dd = (min_row.close / row.close - 1.0) * 100.0
        is_true = dd <= CRASH_DRAWDOWN_PCT
        true_events += int(is_true)
        false_events += int(not is_true)
        diagnostics.append({
            "day": row.day,
            "score": row.score,
            "coverage": row.coverage,
            "forward_20row_min_drawdown_pct": round(dd, 2),
            "forward_trough_day": min_row.day,
            "true_crash_event": is_true,
        })

    complete = true_events + false_events
    precision = true_events / complete if complete else None
    false_alarm_rate = false_events / complete if complete else None
    coverage_ok_share = sum(1 for x in blind if x.coverage >= 0.50) / len(blind)

    # Descriptive holdout drawdown: no threshold fitting and no ex-post regime labels.
    peak = blind[0]
    max_dd = 0.0
    max_dd_peak = peak.day
    max_dd_trough = peak.day
    for row in blind:
        if row.close > peak.close:
            peak = row
        dd = (row.close / peak.close - 1.0) * 100.0
        if dd < max_dd:
            max_dd = dd
            max_dd_peak = peak.day
            max_dd_trough = row.day

    payload = {
        "release": "R0.6.1 Blind Crash Replay",
        "status": "PASS" if coverage_ok_share >= 0.90 else "DATA_QUALITY_FAIL",
        "blind_window": {"start": BLIND_START, "end": BLIND_END},
        "source": "MOEX ISS + official IMOEX point-in-time calculation bases",
        "source_ref": OFFICIAL_CONSTITUENTS_SOURCE,
        "methodology": {
            "threshold_refit": False,
            "exit_gate": asdict(CALIBRATED_EXIT_GATE),
            "forward_rows": FORWARD_ROWS,
            "crash_drawdown_pct": CRASH_DRAWDOWN_PCT,
            "note": "Holdout begins after the four R0.6 calibration episodes. Frozen production EXIT parameters are used unchanged.",
        },
        "data_quality": {
            "blind_rows": len(blind),
            "coverage_ok_share": round(coverage_ok_share, 4),
            "requested_secids": len(all_secids),
            "usable_secids": len(universe),
            "failed_secids": failures,
        },
        "blind_results": {
            "exit_events": len(events),
            "events_with_full_horizon": complete,
            "true_crash_events": true_events,
            "false_events": false_events,
            "precision": round(precision, 4) if precision is not None else None,
            "false_alarm_rate": round(false_alarm_rate, 4) if false_alarm_rate is not None else None,
            "event_diagnostics": diagnostics,
            "max_peak_to_trough_drawdown_pct": round(max_dd, 2),
            "max_drawdown_peak_day": max_dd_peak,
            "max_drawdown_trough_day": max_dd_trough,
        },
        "interpretation_rule": "R0.6.1 reports blind evidence only. It does not refit thresholds and does not promote a new production rule.",
    }
    out = Path("artifacts/blind_crash_replay.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
