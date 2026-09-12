from __future__ import annotations

import json
from pathlib import Path

SNAPSHOT = Path("data/crypto-radar/snapshot.json")
HISTORY = Path("data/crypto-radar/history.json")
MAX_RECORDS = 30 * 24 * 4  # 30 days at 15-minute cadence


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    s = load_json(SNAPSHOT, None)
    if not isinstance(s, dict):
        raise SystemExit("snapshot missing or invalid")

    ts = s.get("generated_at")
    if not ts:
        raise SystemExit("snapshot.generated_at missing")

    m = s.get("market") or {}
    d = s.get("derivatives") or {}
    c = s.get("crowd") or {}
    r = s.get("risk") or {}
    g = s.get("regime") or {}
    t = s.get("transition") or {}
    a = s.get("action_engine") or {}

    record = {
        "generated_at": ts,
        "btc_price": d.get("btc_price"),
        "btc_change_24h_pct": d.get("price_change_24h_pct"),
        "total_change_24h_pct": m.get("total_change_24h_pct"),
        "crowd_score": c.get("score"),
        "crowd_state": c.get("state"),
        "risk_score": r.get("score"),
        "risk_status": r.get("status"),
        "regime": g.get("status"),
        "regime_candidate": g.get("candidate"),
        "regime_confirmed": bool(g.get("confirmed")),
        "candidate_count": g.get("candidate_count"),
        "transition": t.get("status") or g.get("transition"),
        "investor_action": a.get("investor"),
        "trader_action": a.get("trader"),
        "quality_ready": bool(c.get("quality_passed")),
    }

    data = load_json(HISTORY, {"version": "1.6", "records": []})
    if not isinstance(data, dict):
        data = {"version": "1.6", "records": []}
    records = data.get("records")
    if not isinstance(records, list):
        records = []

    # Idempotent on timestamp: replace same observation, never duplicate it.
    by_ts = {x.get("generated_at"): x for x in records if isinstance(x, dict) and x.get("generated_at")}
    by_ts[ts] = record
    records = sorted(by_ts.values(), key=lambda x: x["generated_at"])[-MAX_RECORDS:]

    confirmed_transitions = 0
    regime_changes = 0
    prev_regime = None
    for x in records:
        rg = x.get("regime")
        if x.get("regime_confirmed") and rg and rg != prev_regime:
            confirmed_transitions += 1
        if prev_regime is not None and rg and rg != prev_regime:
            regime_changes += 1
        if rg:
            prev_regime = rg

    out = {
        "version": "1.6",
        "cadence_minutes": 15,
        "retention_records": MAX_RECORDS,
        "record_count": len(records),
        "first_generated_at": records[0]["generated_at"] if records else None,
        "last_generated_at": records[-1]["generated_at"] if records else None,
        "confirmed_transition_count": confirmed_transitions,
        "regime_change_count": regime_changes,
        "records": records,
    }
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "history_records": len(records),
        "last": out["last_generated_at"],
        "confirmed_transitions": confirmed_transitions,
        "regime_changes": regime_changes,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
