from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from moex_crash_radar.crowd_history import build_daily_crowd_evidence, serialize_rows, transition_counts
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


def episode_summary(rows, name: str, start: str, end: str) -> dict:
    sample = [r for r in rows if start <= r.day <= end]
    if not sample:
        return {"name": name, "status": "NO_DATA"}

    valid = [r for r in sample if r.crowd_score is not None]
    if not valid:
        return {"name": name, "status": "DATA_INSUFFICIENT"}

    trough = min(sample, key=lambda x: x.close)
    peak_score_row = max(valid, key=lambda x: x.crowd_score)
    low_score_row = min(valid, key=lambda x: x.crowd_score)
    first_euphoria = next((r for r in valid if r.crowd_state == "EUPHORIA"), None)
    first_fear_or_panic = next((r for r in valid if r.crowd_state in ("FEAR", "PANIC")), None)
    fast_weakening = [r for r in valid if r.direction == "FALLING_FAST"]

    return {
        "name": name,
        "status": "OK",
        "start": sample[0].day,
        "end": sample[-1].day,
        "trough_day": trough.day,
        "trough_close": trough.close,
        "max_crowd_score": peak_score_row.crowd_score,
        "max_crowd_day": peak_score_row.day,
        "min_crowd_score": low_score_row.crowd_score,
        "min_crowd_day": low_score_row.day,
        "first_euphoria_day": first_euphoria.day if first_euphoria else None,
        "first_fear_or_panic_day": first_fear_or_panic.day if first_fear_or_panic else None,
        "fast_weakening_days": len(fast_weakening),
        "transitions": transition_counts(sample),
    }


def main() -> None:
    start = "2019-09-01"
    end = "2026-08-27"
    constituents = load_constituents()
    secids = sorted({secid for basket in constituents.values() for secid in basket})

    index = fetch_index_history("IMOEX", start=start, end=end)
    if len(index) < 200:
        raise SystemExit(f"insufficient IMOEX history: {len(index)}")

    universe = {}
    failures: dict[str, str] = {}
    for secid in secids:
        try:
            candles = fetch_share_history(secid, start=start, end=end)
            if candles:
                universe[secid] = candles
            else:
                failures[secid] = "no candles"
        except Exception as exc:
            failures[secid] = f"{type(exc).__name__}: {exc}"

    rows = build_daily_crowd_evidence(
        index,
        universe,
        min_equity_coverage=0.50,
        warmup=60,
        universe_by_effective_date=constituents,
    )
    if not rows:
        raise SystemExit("no crowd evidence generated")

    valid = [r for r in rows if r.crowd_score is not None]
    coverage_share = len(valid) / len(rows)
    state_counts: dict[str, int] = {}
    for row in valid:
        state_counts[row.crowd_state] = state_counts.get(row.crowd_state, 0) + 1

    velocities = [abs(r.velocity) for r in valid if r.velocity is not None]
    payload = {
        "release": "R0.8.1 Historical Crowd Replay",
        "status": "RESEARCH_ONLY",
        "source": "MOEX ISS + official point-in-time IMOEX constituents",
        "range": {"start": start, "end": end},
        "methodology": {
            "look_ahead": False,
            "positioning_in_score": False,
            "production_weight": False,
            "crowd_score_is_probability": False,
            "rule": "Research composite only. Frozen Crash/EXIT engine is not modified.",
        },
        "data_quality": {
            "index_rows": len(index),
            "requested_secids": len(secids),
            "usable_secids": len(universe),
            "failed_secids": failures,
            "crowd_rows": len(rows),
            "valid_crowd_rows": len(valid),
            "valid_share": round(coverage_share, 4),
            "gate_pass": coverage_share >= 0.90,
        },
        "distribution": {
            "state_counts": state_counts,
            "transitions": transition_counts(rows),
            "median_abs_daily_velocity": round(median(velocities), 2) if velocities else None,
        },
        "episodes": [episode_summary(rows, *episode) for episode in EPISODES],
        "latest": serialize_rows(rows[-1:])[0],
        "rows": serialize_rows(rows),
    }

    out = Path("artifacts/crowd_replay.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
