from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.market_risk import (
    IndependentMarketRiskInputs,
    calculate_independent_market_risk,
)
from moex_crash_radar.moex import fetch_index_history, fetch_share_history

CONSTITUENTS_FILE = Path("data/imoex_constituents_2019_2026.json")
EPISODES = (
    ("COVID_2020", "2020-01-10", "2020-05-15"),
    ("FEB_2022", "2022-01-10", "2022-05-31"),
    ("SEP_2022", "2022-08-01", "2022-11-30"),
    ("CORRECTION_2024", "2024-05-01", "2024-09-30"),
    ("MARKET_2025_2026", "2025-01-01", "2026-08-27"),
)


def load_constituents() -> dict[str, tuple[str, ...]]:
    payload = json.loads(CONSTITUENTS_FILE.read_text(encoding="utf-8"))
    bases = payload.get("bases") or {}
    if not bases:
        raise SystemExit("official IMOEX constituent bases are empty")
    return {day: tuple(codes) for day, codes in sorted(bases.items())}


def episode_summary(rows: list[dict], name: str, start: str, end: str) -> dict:
    sample = [r for r in rows if start <= r["day"] <= end and r["risk_score"] is not None]
    if not sample:
        return {"name": name, "status": "DATA_INSUFFICIENT"}
    trough = min(sample, key=lambda r: r["close"])
    high = next((r for r in sample if r["risk_level"] in ("HIGH", "CRITICAL") and r["day"] <= trough["day"]), None)
    rising_fast = next((r for r in sample if r["risk_direction"] == "RISING_FAST" and r["day"] <= trough["day"]), None)
    return {
        "name": name,
        "status": "OK",
        "trough_day": trough["day"],
        "first_high_or_critical_day": high["day"] if high else None,
        "first_rising_fast_day": rising_fast["day"] if rising_fast else None,
        "trough_risk_score": trough["risk_score"],
        "max_pre_trough_risk_score": max(r["risk_score"] for r in sample if r["day"] <= trough["day"]),
    }


def main() -> None:
    start, end = "2019-09-01", "2026-08-27"
    constituents = load_constituents()
    secids = sorted({s for basket in constituents.values() for s in basket})
    index = fetch_index_history("IMOEX", start=start, end=end)
    if len(index) < 200:
        raise SystemExit(f"insufficient IMOEX history: {len(index)}")

    universe = {}
    failures = {}
    for secid in secids:
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
        min_equity_coverage=0.70,
        warmup=60,
        universe_by_effective_date=constituents,
    )

    rows: list[dict] = []
    prior = None
    for row in evidence:
        result = calculate_independent_market_risk(
            IndependentMarketRiskInputs(
                market_structure=row.market_structure_score,
                breadth=row.breadth_score,
                volatility_liquidity=row.volatility_liquidity_score,
                volume_distribution=row.volume_distribution_score,
            ),
            prior_score=prior,
        )
        if result.score is not None:
            prior = result.score
        rows.append({
            "day": row.day,
            "close": row.close,
            "risk_score": result.score,
            "risk_level": result.state.value,
            "coverage": result.coverage,
            "available_groups": result.available_groups,
            "risk_velocity": result.velocity,
            "risk_direction": result.direction,
            "reasons": list(result.reasons),
            "crash_score_reference": row.score,
        })

    valid = [r for r in rows if r["risk_score"] is not None]
    coverage = len(valid) / len(rows) if rows else 0.0
    state_counts: dict[str, int] = {}
    for row in valid:
        state_counts[row["risk_level"]] = state_counts.get(row["risk_level"], 0) + 1
    velocities = [abs(r["risk_velocity"]) for r in valid if r["risk_velocity"] is not None]

    payload = {
        "release": "R0.9 Independent Market Risk Engine - Historical Replay",
        "status": "RESEARCH_ONLY",
        "source": "MOEX ISS + official point-in-time IMOEX constituents",
        "range": {"start": start, "end": end},
        "methodology": {
            "look_ahead": False,
            "crowd_in_score": False,
            "context_in_score": False,
            "positioning_in_score": False,
            "frozen_crash_exit_in_score": False,
            "production_weight": False,
            "score_is_probability": False,
            "rule": "Independent market-only risk composite; frozen Crash/EXIT is reference only and is not modified.",
        },
        "data_quality": {
            "rows": len(rows),
            "valid_rows": len(valid),
            "valid_share": round(coverage, 4),
            "gate_pass": coverage >= 0.90,
            "requested_secids": len(secids),
            "usable_secids": len(universe),
            "failed_secids": failures,
        },
        "distribution": {
            "state_counts": state_counts,
            "median_abs_daily_velocity": round(median(velocities), 2) if velocities else None,
        },
        "episodes": [episode_summary(rows, *ep) for ep in EPISODES],
        "latest": rows[-1] if rows else None,
        "rows": rows,
    }

    out = Path("artifacts/market_risk_replay.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
