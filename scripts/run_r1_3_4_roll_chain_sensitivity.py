from __future__ import annotations

import argparse
import json
from functools import partial

from moex_crash_radar.contract_costs import fetch_contract_spec
from moex_crash_radar.futures_data import fetch_futures_history
from moex_crash_radar.public_baseline import BaselineConfig
from moex_crash_radar.risk_sensitivity import assess_plateau, chronological_splits, sensitivity_grid
from moex_crash_radar.roll_chain import build_roll_chain


PREFIXES = {"MX": "MX", "SI": "Si", "SR": "SR", "GZ": "GZ", "LK": "LK"}


def _floats(value: str) -> tuple[float, ...]:
    return tuple(float(x.strip()) for x in value.split(",") if x.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="R1.3.4 historical roll-chain & risk-gate sensitivity")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-08-31")
    parser.add_argument("--families", default="MX,SI,SR,GZ,LK")
    parser.add_argument("--stop-atrs", default="1.25,1.5,1.75,2.0")
    parser.add_argument("--min-rrs", default="1.5,1.75,2.0,2.25")
    parser.add_argument("--roll-business-days", type=int, default=5)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--min-positive-share", type=float, default=0.60)
    parser.add_argument("--slippage-ticks-rt", type=float, default=1.0)
    parser.add_argument("--broker-fee-rub-rt", type=float, default=0.0)
    parser.add_argument("--chunk-days", type=int, default=30)
    args = parser.parse_args()

    stop_atrs, min_rrs = _floats(args.stop_atrs), _floats(args.min_rrs)
    families = [x.strip().upper() for x in args.families.split(",") if x.strip()]
    fetcher = partial(fetch_futures_history, chunk_days=max(args.chunk_days, 1))
    base = BaselineConfig(fee_bps_round_trip=0.0, slippage_bps_round_trip=0.0)
    family_reports = []
    hard_errors = []

    for family in families:
        prefix = PREFIXES.get(family, family)
        try:
            chain = build_roll_chain(
                family,
                start=args.start,
                end=args.end,
                secid_prefix=prefix,
                roll_business_days=args.roll_business_days,
                fetcher=fetcher,
            )
            used = sorted({row.secid for row in chain.bars})
            specs = {}
            for secid in used:
                try:
                    spec = fetch_contract_spec(
                        secid,
                        broker_fee_rub_round_trip=args.broker_fee_rub_rt,
                        slippage_ticks_round_trip=args.slippage_ticks_rt,
                    )
                except Exception:
                    spec = None
                if spec is not None:
                    specs[secid] = spec

            split_reports = {}
            splits = chronological_splits(chain.bars)
            for split_name, bars in splits.items():
                points = sensitivity_grid(
                    bars,
                    max_stop_atrs=stop_atrs,
                    min_rrs=min_rrs,
                    base_config=base,
                    specs=specs,
                )
                assessments = {
                    model: assess_plateau(
                        points, model,
                        min_trades=args.min_trades,
                        min_positive_share=args.min_positive_share,
                    ).to_dict()
                    for model in ("M0", "M1", "M5")
                }
                split_reports[split_name] = {
                    "bars": len(bars),
                    "points": [p.to_dict() for p in points],
                    "plateau": assessments,
                }

            validation_ok = any(v["stable_positive"] for v in split_reports["VALIDATION"]["plateau"].values())
            oos_ok = any(v["stable_positive"] for v in split_reports["OOS"]["plateau"].values())
            family_status = "PASS" if chain.bars and validation_ok and oos_ok else ("NO-GO" if chain.bars else "N/A")
            family_reports.append({
                "family": family,
                "status": family_status,
                "roll_chain": chain.diagnostics(),
                "cost_specs": [spec.to_dict() for spec in specs.values()],
                "cost_spec_coverage_pct": round(100.0 * len(specs) / len(used), 2) if used else 100.0,
                "splits": split_reports,
            })
        except Exception as exc:
            hard_errors.append(f"{family}: {type(exc).__name__}: {exc}")
            family_reports.append({"family": family, "status": "ERROR", "error": hard_errors[-1]})

    measurable = [r for r in family_reports if r.get("status") not in {"ERROR", "N/A"}]
    pass_families = [r for r in family_reports if r.get("status") == "PASS"]
    research_go = bool(measurable) and len(pass_families) >= max(2, len(measurable) // 2 + 1)
    report = {
        "gate": "R1.3.4_HISTORICAL_ROLL_CHAIN_RISK_GATE_SENSITIVITY",
        "period": {"start": args.start, "end": args.end},
        "models": ["M0", "M1", "M5"],
        "grid": {"max_stop_atr": stop_atrs, "min_rr": min_rrs},
        "roll_policy": {
            "type": "CALENDAR_QUARTERLY",
            "expiry_proxy": "THIRD_THURSDAY",
            "roll_business_days_before_expiry": args.roll_business_days,
            "no_cross_contract_backfill": True,
            "features_reset_at_roll": True,
        },
        "execution_cost_policy": {
            "tick_geometry": "MOEX_ISS_MINSTEP_STEPPRICE_WHEN_AVAILABLE",
            "broker_fee_rub_round_trip": args.broker_fee_rub_rt,
            "slippage_ticks_round_trip": args.slippage_ticks_rt,
            "missing_spec": "GROSS_METRIC_WITH_EXPLICIT_COVERAGE",
        },
        "validation": {
            "split": "CHRONOLOGICAL_60_20_20_IS_VALIDATION_OOS",
            "min_trades_per_point": args.min_trades,
            "stable_plateau_positive_share": args.min_positive_share,
            "selection_rule": "NO_BEST_POINT_OPTIMIZATION",
        },
        "status": "GO" if research_go and not hard_errors else "NO-GO",
        "hard_errors": hard_errors,
        "families": family_reports,
        "interpretation": (
            "GO requires broad positive parameter plateaus to survive chronological validation and OOS across a majority of measurable families. "
            "A single best grid point is never sufficient. FUTOI/OI positioning remains outside this public baseline release."
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if hard_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
