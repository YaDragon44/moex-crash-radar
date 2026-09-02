from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from moex_crash_radar.bubble_history import historical_bubble_points
from moex_crash_radar.bubble_validation import BubbleEpisode, validate_bubble
from moex_crash_radar.calibration import signal_event_indices
from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.live_gate import CALIBRATED_EXIT_GATE
from moex_crash_radar.moex import fetch_index_history, fetch_share_history

UNIVERSE = (
    "SBER", "SBERP", "LKOH", "GAZP", "YDEX", "T", "X5", "GMKN",
    "NVTK", "ROSN", "TATN", "TATNP", "PLZL", "CHMF", "NLMK", "ALRS",
    "MOEX", "MTSS", "PHOR", "IRAO", "HYDR", "AFLT", "VKCO", "OZON",
)
EPISODES = (
    BubbleEpisode("COVID_2020", "2020-01-10", "2020-03-18"),
    BubbleEpisode("FEB_2022", "2022-01-10", "2022-02-24"),
    BubbleEpisode("SEP_2022", "2022-08-01", "2022-10-10"),
    BubbleEpisode("CORRECTION_2024", "2024-05-01", "2024-09-03"),
)


def main() -> None:
    start, end = "2019-09-01", "2026-08-27"
    index = fetch_index_history("IMOEX", start=start, end=end)
    universe, failures = {}, {}
    for secid in UNIVERSE:
        try:
            rows = fetch_share_history(secid, start=start, end=end)
            if len(rows) >= 60:
                universe[secid] = rows
            else:
                failures[secid] = f"only {len(rows)} candles"
        except Exception as exc:
            failures[secid] = f"{type(exc).__name__}: {exc}"

    evidence = build_daily_evidence(index, universe, min_equity_coverage=0.50, warmup=60)
    points = historical_bubble_points(evidence)
    p = CALIBRATED_EXIT_GATE
    exit_indices = signal_event_indices(
        evidence,
        score_threshold=p.score_threshold,
        confirmations=p.confirmations,
        persistence=p.persistence,
        max_5d_return_pct=p.max_5d_return_pct,
        cooldown_rows=p.cooldown_rows,
        require_breadth_volume=p.require_breadth_volume,
        rearm_clear_rows=p.rearm_clear_rows,
    )
    exit_days = [evidence[i].day for i in exit_indices]

    candidates = [
        validate_bubble(evidence, points, EPISODES, threshold=t, exit_event_days=exit_days)
        for t in (45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0)
    ]
    valid = [c for c in candidates if c.status == "GO_FOR_BUBBLE_INTEGRATION_REVIEW"]
    preferred = max(valid, key=lambda c: (c.median_advance_vs_exit_days or -999, -(c.false_event_rate or 1))) if valid else None

    scored = [p for p in points if p.score is not None]
    payload = {
        "release": "R0.5.4.1 Bubble Historical Replay",
        "status": preferred.status if preferred else ("DATA_GATE_FAIL_NO_DECISION" if not scored or len(scored) / len(points) < .60 else "NO_GO_KEEP_RESEARCH_ONLY"),
        "source": "MOEX ISS",
        "range": {"start": start, "end": end},
        "data_gate": {
            "evidence_rows": len(evidence),
            "bubble_scored_rows": len(scored),
            "bubble_scored_share": round(len(scored) / len(points), 4) if points else 0,
            "usable_equities": len(universe),
            "failed_equities": failures,
        },
        "methodology": {
            "point_in_time": True,
            "look_ahead": False,
            "live_exit_gate_unchanged": True,
            "bubble_is_probability": False,
            "historical_proxy_groups": ["price_stretch", "breadth_fragility", "volatility_complacency", "narrow_leadership_proxy"],
            "missing_until_sourced": ["valuation", "true_index_concentration", "leverage", "crowd_euphoria"],
            "warning": "Narrow leadership is an index-vs-breadth proxy, not true historical constituent concentration. Current liquid equity universe creates survivorship/listing-history bias.",
        },
        "frozen_exit_gate": asdict(p),
        "exit_event_days": exit_days,
        "episodes": [asdict(x) for x in EPISODES],
        "candidates": [asdict(x) for x in candidates],
        "preferred": asdict(preferred) if preferred else None,
    }
    out = Path("artifacts/bubble_historical_validation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
