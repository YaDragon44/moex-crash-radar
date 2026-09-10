from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from statistics import median

from moex_crash_radar.positioning import fetch_futoi

HISTORICAL_FILE = Path("artifacts/historical_evidence.json")
BLIND_FILE = Path("artifacts/blind_crash_replay.json")
OUT_FILE = Path("artifacts/positioning_incremental_value.json")
TICKER = "MX"
LOOKBACK_CALENDAR_DAYS = 12
MIN_PAIRED_DAYS = 3


def latest_by_group(rows):
    out = {}
    for row in rows:
        cur = out.get(row.client_group)
        rank = ((row.moment or ""), row.seqnum if row.seqnum is not None else -1)
        if cur is None:
            out[row.client_group] = row
            continue
        cur_rank = ((cur.moment or ""), cur.seqnum if cur.seqnum is not None else -1)
        if rank > cur_rank:
            out[row.client_group] = row
    return out


def paired_day(day: str):
    rows = fetch_futoi(TICKER, start=day, end=day)
    latest = latest_by_group(rows)
    fiz = latest.get("FIZ")
    yur = latest.get("YUR")
    if not fiz or not yur:
        return None
    gross = fiz.long_contracts + fiz.short_contracts + yur.long_contracts + yur.short_contracts
    oi = gross / 2.0
    if oi <= 0:
        return None
    long_side = fiz.long_contracts + yur.long_contracts
    short_side = fiz.short_contracts + yur.short_contracts
    balance_error_share = abs(long_side - short_side) / oi
    return {
        "day": day,
        "oi": oi,
        "retail_net_share": fiz.net_position / oi,
        "legal_net_share": yur.net_position / oi,
        "retail_long_share": fiz.long_contracts / max(1.0, fiz.long_contracts + fiz.short_contracts),
        "balance_error_share": balance_error_share,
    }


def event_features(event_day: str):
    center = date.fromisoformat(event_day)
    paired = []
    errors = []
    calls = 0
    for offset in range(LOOKBACK_CALENDAR_DAYS + 1):
        d = (center - timedelta(days=offset)).isoformat()
        try:
            row = paired_day(d)
        except Exception as exc:
            errors.append({"day": d, "error": f"{type(exc).__name__}: {exc}"})
            row = None
        calls += 1
        if row:
            paired.append(row)
    paired.sort(key=lambda x: x["day"])
    if len(paired) < MIN_PAIRED_DAYS:
        return None, calls, errors

    latest = paired[-1]
    base = paired[max(0, len(paired) - 6)]
    oi_change = (latest["oi"] / base["oi"] - 1.0) if base["oi"] else None
    retail_delta = latest["retail_net_share"] - base["retail_net_share"]
    return {
        "as_of": latest["day"],
        "paired_days": len(paired),
        "retail_net_share": round(latest["retail_net_share"], 6),
        "legal_net_share": round(latest["legal_net_share"], 6),
        "retail_long_share": round(latest["retail_long_share"], 6),
        "oi_change_5obs": round(oi_change, 6) if oi_change is not None else None,
        "retail_net_share_change_5obs": round(retail_delta, 6),
        "balance_error_share": round(latest["balance_error_share"], 8),
    }, calls, errors


def load_labeled_events():
    hist = json.loads(HISTORICAL_FILE.read_text(encoding="utf-8"))
    blind = json.loads(BLIND_FILE.read_text(encoding="utf-8"))
    calibration = []
    for row in hist["frozen_exit_validation"]["event_diagnostics"]:
        day = row["day"]
        if day <= "2024-09-30":
            calibration.append({"day": day, "true_crash_event": not bool(row["false_event"]), "split": "calibration"})
    holdout = []
    for row in blind["blind_results"]["event_diagnostics"]:
        if row.get("status") == "INCOMPLETE_FORWARD_HORIZON":
            continue
        holdout.append({"day": row["day"], "true_crash_event": bool(row["true_crash_event"]), "split": "holdout"})
    return calibration, holdout


def metrics(rows, feature, threshold, direction):
    usable = [r for r in rows if r.get("features") and r["features"].get(feature) is not None]
    if not usable:
        return None
    def keep(r):
        value = r["features"][feature]
        return value >= threshold if direction == ">=" else value <= threshold
    tp = sum(1 for r in usable if r["true_crash_event"] and keep(r))
    fn = sum(1 for r in usable if r["true_crash_event"] and not keep(r))
    fp = sum(1 for r in usable if not r["true_crash_event"] and keep(r))
    tn = sum(1 for r in usable if not r["true_crash_event"] and not keep(r))
    recall = tp / (tp + fn) if tp + fn else None
    false_alarm_rate = fp / (fp + tn) if fp + tn else None
    precision = tp / (tp + fp) if tp + fp else None
    return {
        "usable_events": len(usable), "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "recall": round(recall, 4) if recall is not None else None,
        "false_alarm_rate": round(false_alarm_rate, 4) if false_alarm_rate is not None else None,
        "precision": round(precision, 4) if precision is not None else None,
    }


def candidate_rules(calibration):
    features = (
        "retail_net_share",
        "retail_long_share",
        "oi_change_5obs",
        "retail_net_share_change_5obs",
    )
    candidates = []
    for feature in features:
        values = [r["features"][feature] for r in calibration if r.get("features") and r["features"].get(feature) is not None]
        if len(values) < 4:
            continue
        threshold = median(values)
        for direction in (">=", "<="):
            m = metrics(calibration, feature, threshold, direction)
            if not m:
                continue
            candidates.append({"feature": feature, "threshold": threshold, "direction": direction, "calibration": m})
    # Safety first: a positioning filter is only admissible if it does not remove any known calibration crash event.
    admissible = [x for x in candidates if x["calibration"]["recall"] == 1.0]
    admissible.sort(key=lambda x: (x["calibration"]["false_alarm_rate"] if x["calibration"]["false_alarm_rate"] is not None else 1.0, -x["calibration"]["precision"] if x["calibration"]["precision"] is not None else 0.0))
    return candidates, (admissible[0] if admissible else None)


def main():
    calibration_labels, holdout_labels = load_labeled_events()
    all_rows = []
    total_calls = 0
    total_errors = 0
    for label in calibration_labels + holdout_labels:
        features, calls, errors = event_features(label["day"])
        total_calls += calls
        total_errors += len(errors)
        all_rows.append({**label, "features": features, "errors": errors})

    calibration = [r for r in all_rows if r["split"] == "calibration"]
    holdout = [r for r in all_rows if r["split"] == "holdout"]
    coverage = sum(1 for r in all_rows if r["features"]) / len(all_rows) if all_rows else 0.0
    candidates, selected = candidate_rules(calibration)

    verdict = "NO_INCREMENTAL_VALUE"
    holdout_result = None
    rationale = "No calibration rule preserved 100% crash recall."
    if coverage < 0.80:
        verdict = "DATA_QUALITY_FAIL"
        rationale = "Positioning feature coverage is below 80%."
    elif selected:
        holdout_result = metrics(holdout, selected["feature"], selected["threshold"], selected["direction"])
        if holdout_result and holdout_result["recall"] == 1.0 and holdout_result["false_alarm_rate"] is not None and holdout_result["false_alarm_rate"] < 1.0:
            verdict = "CANDIDATE_VALUE"
            rationale = "A calibration-only univariate filter preserved all holdout crash events and removed at least one holdout false alarm. Further validation is required before production use."
        else:
            rationale = "Best calibration-only filter did not prove safer false-alarm reduction on holdout."

    payload = {
        "release": "R0.7.2 Positioning Incremental Value Test",
        "status": verdict,
        "ticker": TICKER,
        "source": "MOEX ISS analyticalproducts/futoi",
        "methodology": {
            "purpose": "Test whether positioning can filter frozen EXIT events without changing Crash Score or EXIT thresholds.",
            "feature_window": f"event day plus prior {LOOKBACK_CALENDAR_DAYS} calendar days; only same/past positioning data",
            "candidate_model": "single-feature median threshold fitted on calibration only",
            "admissibility": "100% calibration crash-event recall required",
            "holdout_rule": "candidate must retain 100% holdout crash-event recall and remove at least one holdout false alarm",
            "no_threshold_refit": True,
            "no_crash_score_change": True,
            "no_production_weight": True,
        },
        "quality_gate": {
            "event_count": len(all_rows),
            "events_with_features": sum(1 for r in all_rows if r["features"]),
            "coverage": round(coverage, 4),
            "api_calls": total_calls,
            "failed_calls": total_errors,
        },
        "selected_candidate": selected,
        "holdout_result": holdout_result,
        "rationale": rationale,
        "events": all_rows,
        "candidate_rules": candidates,
        "decision_rule": "CANDIDATE_VALUE is research-only. Production Crash/EXIT remains frozen until a separate validation gate explicitly approves a positioning rule.",
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
