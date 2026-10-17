from __future__ import annotations

import argparse
import json
from pathlib import Path

from moex_crash_radar.oi_flow_audit import audit_futoi_history, public_safe_end


DEFAULT_CONFIG = Path("config/oi_flow_universe_v1.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit historical MOEX FUTOI coverage for the OI Flow 1H universe")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--output", default="artifacts/oi_flow_universe_audit.json")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    end = args.end or public_safe_end()
    results = []
    for instrument in config["instruments"]:
        ticker = instrument["futoi_ticker"]
        try:
            audit = audit_futoi_history(ticker, start=args.start, end=end)
            row = audit.to_dict()
        except Exception as exc:  # fail closed: transport/access errors are not READY
            row = {
                "ticker": ticker,
                "start": args.start,
                "end": end,
                "rows": 0,
                "paired_snapshots": 0,
                "unique_days": 0,
                "first_moment": None,
                "last_moment": None,
                "point_in_time_violations": 0,
                "status": "N/A",
                "note": f"Audit source error: {type(exc).__name__}: {exc}",
            }
        row["research_id"] = instrument["research_id"]
        row["underlying"] = instrument["underlying"]
        results.append(row)

    ready = sum(1 for r in results if r["status"] == "READY")
    payload = {
        "version": "R1.3.2",
        "start": args.start,
        "end": end,
        "universe_size": len(results),
        "ready_instruments": ready,
        "quality_coverage_pct": round(ready / len(results) * 100.0, 2) if results else 0.0,
        "results": results,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
