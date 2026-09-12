from __future__ import annotations

import json
from pathlib import Path
from statistics import median, mean
from math import sqrt

SRC = Path("artifacts/market_risk_replay.json")
OUT = Path("artifacts/market_risk_duplication_gate.json")


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    denx = sqrt(sum((x-mx)**2 for x in xs))
    deny = sqrt(sum((y-my)**2 for y in ys))
    if denx == 0 or deny == 0:
        return None
    return num/(denx*deny)


def main():
    if not SRC.exists():
        raise SystemExit("market_risk_replay.json missing")
    payload = json.loads(SRC.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    pairs = [
        (float(r["risk_score"]), float(r["crash_score_reference"]))
        for r in rows
        if r.get("risk_score") is not None and r.get("crash_score_reference") is not None
    ]
    if len(pairs) < 200:
        raise SystemExit(f"insufficient paired rows: {len(pairs)}")
    risk = [a for a,_ in pairs]
    crash = [b for _,b in pairs]
    diffs = [abs(a-b) for a,b in pairs]
    corr = pearson(risk, crash)
    med_abs = median(diffs)
    mean_abs = mean(diffs)

    # Independent Risk must not be a cosmetic re-scaling of frozen Crash.
    # Predeclared research gate: correlation below 0.95 OR median abs deviation >= 5.
    non_duplicate = bool((corr is not None and corr < 0.95) or med_abs >= 5.0)
    result = {
        "release": "R0.9.1 Market Risk Duplication Gate",
        "status": "GO_FOR_RISK_VALIDATION" if non_duplicate else "NO_GO_DUPLICATES_CRASH",
        "methodology": {
            "threshold_refit": False,
            "frozen_crash_exit_changed": False,
            "production_weight": False,
            "gate": "Pass only if corr(Risk, Crash) < 0.95 OR median absolute deviation >= 5 points."
        },
        "paired_rows": len(pairs),
        "pearson_correlation": round(corr, 6) if corr is not None else None,
        "median_abs_difference": round(med_abs, 2),
        "mean_abs_difference": round(mean_abs, 2),
        "release_gate_pass": non_duplicate,
        "decision": (
            "Risk carries materially different information from frozen Crash."
            if non_duplicate else
            "Current Risk is too close to frozen Crash to justify a separate production engine. Redesign features; do not add another dashboard score."
        )
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
