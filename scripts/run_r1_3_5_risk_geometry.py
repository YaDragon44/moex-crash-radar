from __future__ import annotations

import argparse
import json
from functools import partial

from moex_crash_radar.contract_costs import fetch_contract_spec
from moex_crash_radar.futures_data import fetch_futures_history
from moex_crash_radar.public_baseline import BaselineConfig
from moex_crash_radar.risk_geometry import GEOMETRIES, compare_geometries
from moex_crash_radar.risk_sensitivity import chronological_splits
from moex_crash_radar.roll_chain import build_roll_chain

PREFIXES = {"MX": "MX", "SI": "Si", "SR": "SR", "GZ": "GZ", "LK": "LK"}


def main() -> int:
    p = argparse.ArgumentParser(description="R1.3.5 Risk Geometry Redesign")
    p.add_argument("--start", default="2024-01-01")
    p.add_argument("--end", default="2026-08-31")
    p.add_argument("--families", default="MX,SI,SR,GZ,LK")
    p.add_argument("--roll-business-days", type=int, default=5)
    p.add_argument("--slippage-ticks-rt", type=float, default=1.0)
    p.add_argument("--broker-fee-rub-rt", type=float, default=0.0)
    p.add_argument("--chunk-days", type=int, default=30)
    args = p.parse_args()

    config = BaselineConfig(max_stop_atr=1.5, min_rr=2.0, fee_bps_round_trip=0.0, slippage_bps_round_trip=0.0)
    families = [x.strip().upper() for x in args.families.split(",") if x.strip()]
    history_fetcher = partial(fetch_futures_history, chunk_days=max(args.chunk_days, 1))
    output = []
    for family in families:
        try:
            chain = build_roll_chain(
                family, start=args.start, end=args.end,
                secid_prefix=PREFIXES[family], roll_business_days=args.roll_business_days,
                fetcher=history_fetcher,
            )
            specs = {}
            for secid in sorted({r.secid for r in chain.bars}):
                spec = fetch_contract_spec(
                    secid,
                    broker_fee_rub_round_trip=args.broker_fee_rub_rt,
                    slippage_ticks_round_trip=args.slippage_ticks_rt,
                )
                if spec is not None:
                    specs[secid] = spec
            splits = chronological_splits(chain.bars)
            split_results = {}
            for name, bars in splits.items():
                split_results[name] = [r.to_dict() for r in compare_geometries(bars, config=config, specs=specs)]
            output.append({
                "family": family,
                "status": "READY" if chain.bars else "N/A",
                "coverage": chain.diagnostics(),
                "spec_coverage_pct": round(100.0 * len(specs) / max(len({r.secid for r in chain.bars}), 1), 2),
                "splits": split_results,
            })
        except Exception as exc:
            output.append({"family": family, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})

    qualifying = []
    for family in output:
        if family.get("status") != "READY":
            continue
        rows = family["splits"]["OOS"]
        for model in ("M0", "M1", "M5"):
            control = next(r for r in rows if r["model"] == model and r["geometry"] == "CONTROL")
            for r in rows:
                if r["model"] != model or r["geometry"] == "CONTROL":
                    continue
                if control["accepted"] == 0:
                    ok = (
                        r["accepted"] >= 5
                        and r["expectancy_r"] is not None and r["expectancy_r"] > 0
                        and (r["max_drawdown_r"] or 0) >= -2.0
                    )
                    reason = "ZERO_CONTROL_ABSOLUTE_QUALITY_GATE"
                else:
                    ok = (
                        r["accepted"] >= 2 * control["accepted"]
                        and r["expectancy_r"] is not None and control["expectancy_r"] is not None
                        and r["expectancy_r"] >= control["expectancy_r"] - 0.10
                        and (r["max_drawdown_r"] or 0) >= (control["max_drawdown_r"] or 0) - 2.0
                    )
                    reason = "RELATIVE_TO_CONTROL_GATE"
                if ok:
                    qualifying.append({
                        "family": family["family"], "model": model, "geometry": r["geometry"],
                        "gate_mode": reason, "control": control, "redesign": r,
                    })

    distinct_pairs = {(x["family"], x["model"]) for x in qualifying}
    research_go = len(distinct_pairs) >= 8
    report = {
        "gate": "R1.3.5_RISK_GEOMETRY_REDESIGN_CANDIDATE_PRESERVATION",
        "period": [args.start, args.end],
        "control": "structural swing stop + nearest 1H obstacle",
        "geometries": list(GEOMETRIES),
        "frozen": {"max_stop_atr": 1.5, "min_rr": 2.0, "regime_trigger_location_rvol": True},
        "retrieval": {"chunk_days": args.chunk_days},
        "status": "GO" if research_go else "NO-GO",
        "decision_rule": "GO requires >=8 distinct OOS family/model pairs. With nonzero CONTROL: >=2x trades, expectancy deterioration <=0.10R, DD deterioration <=2R. With zero CONTROL: redesigned geometry requires >=5 trades, positive expectancy, DD >=-2R.",
        "qualifying_oos_pairs": len(distinct_pairs),
        "qualifying_details": qualifying,
        "results": output,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(x.get("status") == "ERROR" for x in output) else 0


if __name__ == "__main__":
    raise SystemExit(main())
