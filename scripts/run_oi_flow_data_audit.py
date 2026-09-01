from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from moex_crash_radar.oi_flow_audit import audit_futoi_history, public_safe_end


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit historical MOEX FUTOI coverage for OI Flow 1H")
    parser.add_argument("--tickers", default="RI,SI", help="Comma-separated FUTOI instrument codes")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    safe_end = args.end or public_safe_end()
    start = args.start or (date.fromisoformat(safe_end) - timedelta(days=30)).isoformat()
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]

    results = []
    exit_code = 0
    for ticker in tickers:
        try:
            result = audit_futoi_history(ticker, start=start, end=safe_end)
        except Exception as exc:  # audit must report source failure, not hide it
            results.append({
                "ticker": ticker.upper(),
                "start": start,
                "end": safe_end,
                "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
            })
            exit_code = 2
        else:
            results.append(result.to_dict())
            if result.status not in {"READY", "N/A"}:
                exit_code = 1

    coverage = sum(1 for r in results if r.get("status") == "READY") / len(results) if results else 0.0
    report = {
        "gate": "R1.3.1_HISTORICAL_FUTOI_DATA_AUDIT",
        "start": start,
        "end": safe_end,
        "quality_coverage_pct": round(coverage * 100.0, 2),
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
