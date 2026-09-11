from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from moex_crash_radar.crowd_history import build_daily_crowd_evidence, transition_counts
from moex_crash_radar.crowd_transition import stable_states
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


def stable_transition_counts(rows) -> dict[str, int]:
    out: dict[str, int] = {}
    previous = None
    for row in rows:
        current = row.stable_state
        if current == "DATA_INSUFFICIENT":
            continue
        if previous is not None and current != previous:
            key = f"{previous}->{current}"
            out[key] = out.get(key, 0) + 1
        previous = current
    return out


def episode_summary(raw_rows, stable_rows, name: str, start: str, end: str) -> dict:
    indexed = {r.day: r for r in raw_rows}
    raw = [r for r in raw_rows if start <= r.day <= end and r.crowd_score is not None]
    stable = [r for r in stable_rows if start <= r.day <= end and r.score is not None]
    if not raw or not stable:
        return {"name": name, "status": "DATA_INSUFFICIENT"}

    trough = min(raw, key=lambda x: x.close)
    first_raw_fear = next((r for r in raw if r.crowd_state in ("FEAR", "PANIC")), None)
    first_stable_fear = next((r for r in stable if r.stable_state in ("FEAR", "PANIC")), None)
    first_falling_fast = next((r for r in stable if r.falling_fast), None)

    def lead(day: str | None) -> int | None:
        if day is None or day > trough.day:
            return None
        return (date.fromisoformat(trough.day) - date.fromisoformat(day)).days

    return {
        "name": name,
        "status": "OK",
        "trough_day": trough.day,
        "raw_first_fear_or_panic": first_raw_fear.day if first_raw_fear else None,
        "stable_first_fear_or_panic": first_stable_fear.day if first_stable_fear else None,
        "first_falling_fast": first_falling_fast.day if first_falling_fast else None,
        "raw_lead_days_to_trough": lead(first_raw_fear.day if first_raw_fear else None),
        "stable_lead_days_to_trough": lead(first_stable_fear.day if first_stable_fear else None),
        "falling_fast_lead_days_to_trough": lead(first_falling_fast.day if first_falling_fast else None),
        "raw_transitions": transition_counts([r for r in raw_rows if start <= r.day <= end]),
        "stable_transitions": stable_transition_counts([r for r in stable_rows if start <= r.day <= end]),
        "trough_crowd_score": indexed[trough.day].crowd_score,
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

    raw = build_daily_crowd_evidence(index, universe, min_equity_coverage=0.50, warmup=60, universe_by_effective_date=constituents)
    stable = stable_states(raw, persistence=3, hysteresis=5.0)
    raw_counts = transition_counts(raw)
    stable_counts = stable_transition_counts(stable)
    raw_total = sum(raw_counts.values())
    stable_total = sum(stable_counts.values())
    reduction = (1.0 - stable_total / raw_total) if raw_total else None

    valid = [r for r in raw if r.crowd_score is not None]
    coverage_share = len(valid) / len(raw) if raw else 0.0
    episodes = [episode_summary(raw, stable, *ep) for ep in EPISODES]

    # Gate is intentionally about stability + preserving crisis warning, not production approval.
    calibration = episodes[:4]
    preserved = sum(1 for e in calibration if e.get("stable_lead_days_to_trough") is not None)
    stability_pass = reduction is not None and reduction >= 0.40
    warning_pass = preserved == len(calibration)
    gate_pass = coverage_share >= 0.90 and stability_pass and warning_pass

    payload = {
        "release": "R0.8.2 Crowd Transition & Stability Validation",
        "status": "GO_FOR_INCREMENTAL_VALUE_TEST" if gate_pass else "RESEARCH_ONLY",
        "methodology": {
            "look_ahead": False,
            "persistence_sessions": 3,
            "hysteresis_points": 5.0,
            "falling_fast_5session_delta": -15.0,
            "threshold_refit": False,
            "frozen_crash_exit_changed": False,
            "production_weight": False,
        },
        "data_quality": {
            "raw_rows": len(raw),
            "valid_rows": len(valid),
            "valid_share": round(coverage_share, 4),
            "requested_secids": len(secids),
            "usable_secids": len(universe),
            "failed_secids": failures,
        },
        "stability": {
            "raw_transition_count": raw_total,
            "stable_transition_count": stable_total,
            "transition_reduction_pct": round(reduction * 100, 2) if reduction is not None else None,
            "raw_transitions": raw_counts,
            "stable_transitions": stable_counts,
            "stability_gate_pass": stability_pass,
        },
        "warning_preservation": {
            "calibration_episodes": len(calibration),
            "episodes_with_stable_fear_warning": preserved,
            "gate_pass": warning_pass,
        },
        "episodes": episodes,
        "release_gate_pass": gate_pass,
        "decision_rule": "Pass only if transition noise falls >=40% while stable FEAR/PANIC warning is preserved in all four calibration crises. Passing does not make Crowd production-ready; it only permits an incremental-value test versus frozen EXIT.",
    }

    out = Path("artifacts/crowd_stability_replay.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
