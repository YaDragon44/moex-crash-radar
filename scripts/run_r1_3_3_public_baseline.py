from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from moex_crash_radar.futures_data import fetch_futures_candles
from moex_crash_radar.public_baseline import BaselineConfig, run_ablation


DEFAULT_CONTRACTS = {
    "MX": "MXU6",
    "SI": "SiU6",
    "SR": "SRU6",
    "GZ": "GZU6",
    "LK": "LKU6",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="R1.3.3 public baseline M0/M1/M5 backtest")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--contracts", default=",".join(f"{k}:{v}" for k, v in DEFAULT_CONTRACTS.items()))
    parser.add_argument("--fee-bps", type=float, default=2.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--min-trades", type=int, default=20)
    args = parser.parse_args()

    config = BaselineConfig(fee_bps_round_trip=args.fee_bps, slippage_bps_round_trip=args.slippage_bps)
    results = []
    for item in args.contracts.split(","):
        family, secid = item.split(":", 1)
        family, secid = family.strip().upper(), secid.strip()
        try:
            candles = fetch_futures_candles(secid, start=args.start, end=args.end, interval=60)
            summaries = run_ablation(candles, config)
            models = {name: summary.to_dict() for name, summary in summaries.items()}
            enough = all(summary.trades >= args.min_trades for summary in summaries.values())
            results.append({
                "family": family,
                "secid": secid,
                "candles": len(candles),
                "first_bar": candles[0].begin if candles else None,
                "last_bar": candles[-1].begin if candles else None,
                "status": "READY" if candles and enough else ("PARTIAL" if candles else "N/A"),
                "models": models,
            })
        except Exception as exc:
            results.append({"family": family, "secid": secid, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})

    gate_ready = all(r.get("status") == "READY" for r in results)
    report = {
        "gate": "R1.3.3_PUBLIC_BASELINE_M0_M1_M5",
        "start": args.start,
        "end": args.end,
        "costs": asdict(config),
        "status": "READY" if gate_ready else "NO-GO",
        "results": results,
        "interpretation": "This baseline tests public price/location/RVOL only. It makes no claim about OI/FUTOI edge.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if gate_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
