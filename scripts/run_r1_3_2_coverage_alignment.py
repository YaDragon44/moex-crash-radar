from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta

from moex_crash_radar.futoi import pair_snapshots, parse_futoi_rows
from moex_crash_radar.oi_flow_audit import FutoiSubscriptionRequired, fetch_futoi_history
from moex_crash_radar.oi_flow_coverage_gate import evaluate_coverage_gate, full_model_gate


def _hourly_decisions_from_pairs(pairs):
    """Create one decision boundary for every clock-hour containing FUTOI data.

    This audits FUTOI -> 1H point-in-time alignment independently from futures
    roll logic. The backtest later intersects these timestamps with actual closed
    1H price bars for the selected concrete contract.
    """
    decisions = set()
    for pair in pairs:
        moment = datetime.fromisoformat(pair.moment)
        close = moment.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        decisions.add(close.isoformat(sep=" "))
    return sorted(decisions)


def main() -> int:
    parser = argparse.ArgumentParser(description="R1.3.2 FUTOI coverage and 1H alignment gate")
    parser.add_argument("--tickers", default="MX,SI,SR,GZ,LK")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--min-coverage", type=float, default=95.0)
    parser.add_argument("--max-median-lag", type=int, default=300)
    args = parser.parse_args()

    results = []
    blocked_auth = []
    for raw_ticker in args.tickers.split(","):
        ticker = raw_ticker.strip().upper()
        if not ticker:
            continue
        try:
            rows = fetch_futoi_history(ticker, start=args.start, end=args.end)
        except FutoiSubscriptionRequired as exc:
            blocked_auth.append(ticker)
            results.append({
                "ticker": ticker,
                "status": "BLOCKED_AUTH",
                "reason": str(exc),
            })
            continue
        except Exception as exc:
            results.append({
                "ticker": ticker,
                "status": "ERROR",
                "reason": f"{type(exc).__name__}: {exc}",
            })
            continue

        pairs = pair_snapshots(parse_futoi_rows(rows))
        decisions = _hourly_decisions_from_pairs(pairs)
        result = evaluate_coverage_gate(
            ticker=ticker,
            pairs=pairs,
            decision_timestamps=decisions,
            min_alignment_coverage_pct=args.min_coverage,
            max_median_publication_lag_sec=args.max_median_lag,
        )
        results.append(result.to_dict())

    measured = [r for r in results if r.get("status") in {"READY", "FAIL", "N/A"}]
    gate = full_model_gate([
        evaluate_coverage_gate(ticker=r["ticker"], pairs=[], decision_timestamps=[])
        for r in []
    ]) if False else None
    ready = [r["ticker"] for r in measured if r.get("status") == "READY"]
    blocked = [r["ticker"] for r in results if r.get("status") != "READY"]
    report = {
        "gate": "R1.3.2_FUTOI_COVERAGE_1H_ALIGNMENT",
        "start": args.start,
        "end": args.end,
        "thresholds": {
            "min_alignment_coverage_pct": args.min_coverage,
            "max_median_publication_lag_sec": args.max_median_lag,
        },
        "status": "READY" if results and not blocked else "NO-GO",
        "ready_tickers": ready,
        "blocked_tickers": blocked,
        "blocked_auth_tickers": blocked_auth,
        "results": results,
        "note": "FUTOI decisions are audited at observed clock-hour boundaries; final backtest must intersect with actual closed 1H contract bars.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
