from __future__ import annotations

import json
from pathlib import Path

from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.moex import fetch_index_history, fetch_share_history

CONSTITUENTS_FILE = Path("data/imoex_constituents_2019_2026.json")
START = "2019-03-22"
END = "2026-09-18"
DEV_END = "2023-12-29"
HOLDOUT_START = "2024-01-01"
HORIZON = 20
DRAWDOWN = -8.0
MIN_COVERAGE = 0.70


def load_constituents():
    payload = json.loads(CONSTITUENTS_FILE.read_text(encoding="utf-8"))
    bases = payload.get("bases") or {}
    if not bases:
        raise SystemExit("official IMOEX constituent bases are empty")
    return {day: tuple(codes) for day, codes in sorted(bases.items())}


def prior_5_return(rows, i):
    if i < 5:
        return None
    return (rows[i].close / rows[i - 5].close - 1.0) * 100.0


def flags(rows, i):
    r = rows[i]
    ret5 = prior_5_return(rows, i)
    usable = (
        r.coverage >= MIN_COVERAGE
        and r.market_structure_score is not None
        and r.breadth_score is not None
        and r.volume_distribution_score is not None
        and r.volatility_liquidity_score is not None
        and ret5 is not None
    )
    if not usable:
        return None
    price = r.market_structure_score < 50 and ret5 > -3.0
    breadth = r.breadth_score >= 40
    volume = r.volume_distribution_score >= 40
    volatility = r.volatility_liquidity_score >= 50
    return {
        "M0": price,
        "M1": price and breadth,
        "M2": price and breadth and volume,
        "M3": price and breadth and volatility,
        "M4": price and breadth and (volume or volatility),
    }


def outcome(rows, i):
    future = rows[i + 1 : i + 1 + HORIZON]
    if len(future) < HORIZON:
        return None
    dd = (min(x.close for x in future) / rows[i].close - 1.0) * 100.0
    return dd <= DRAWDOWN


def metrics(rows, start, end):
    counts = {m: {"alerts": 0, "tp": 0} for m in ("M0", "M1", "M2", "M3", "M4")}
    positives = 0
    usable = 0
    missing = 0
    for i, r in enumerate(rows):
        if not (start <= r.day <= end):
            continue
        y = outcome(rows, i)
        f = flags(rows, i)
        if y is None or f is None:
            missing += 1
            continue
        usable += 1
        positives += int(y)
        for m, alert in f.items():
            if alert:
                counts[m]["alerts"] += 1
                counts[m]["tp"] += int(y)
    out = {}
    for m, c in counts.items():
        fp = c["alerts"] - c["tp"]
        precision = c["tp"] / c["alerts"] if c["alerts"] else None
        recall = c["tp"] / positives if positives else None
        out[m] = {
            **c,
            "false_alarms": fp,
            "precision": round(precision, 4) if precision is not None else None,
            "recall": round(recall, 4) if recall is not None else None,
            "false_alarm_rate": round(fp / c["alerts"], 4) if c["alerts"] else None,
        }
    return {"usable_rows": usable, "missing_rows": missing, "positive_rows": positives, "models": out}


def main():
    constituents = load_constituents()
    secids = sorted({s for basket in constituents.values() for s in basket})
    index = fetch_index_history("IMOEX", start=START, end=END)
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
    rows = build_daily_evidence(index, universe, min_equity_coverage=MIN_COVERAGE, warmup=60, universe_by_effective_date=constituents)
    dev = metrics(rows, START, DEV_END)
    holdout = metrics(rows, HOLDOUT_START, END)
    m0, m4 = holdout["models"]["M0"], holdout["models"]["M4"]
    if holdout["usable_rows"] == 0 or m4["alerts"] == 0 or holdout["positive_rows"] == 0:
        result = "INCONCLUSIVE"
    else:
        p0, p4 = m0["precision"], m4["precision"]
        r0, r4 = m0["recall"], m4["recall"]
        result = "PASS" if (p4 is not None and r4 is not None and p0 is not None and r0 is not None and p4 > p0 and r4 > 0) else "FAIL"
    payload = {
        "release": "R1.5.3-B",
        "result": result,
        "production": "NO-GO",
        "locked": {"range": [START, END], "holdout": [HOLDOUT_START, END], "horizon_sessions": HORIZON, "drawdown_pct": DRAWDOWN, "min_coverage": MIN_COVERAGE},
        "data": {"index_rows": len(index), "evidence_rows": len(rows), "requested_secids": len(secids), "usable_secids": len(universe), "failed_secids": failures},
        "development": dev,
        "holdout": holdout,
        "incremental_m4_vs_m0": {
            "precision_delta": round((m4["precision"] or 0) - (m0["precision"] or 0), 4),
            "recall_delta": round((m4["recall"] or 0) - (m0["recall"] or 0), 4),
        },
        "note": "First locked replay; no retuning. PASS requires holdout M4 precision above M0 and non-zero M4 recall.",
    }
    out = Path("artifacts/r1_5_3b_transition_replay.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
