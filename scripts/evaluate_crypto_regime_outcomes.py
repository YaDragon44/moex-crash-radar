from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HISTORY = Path("data/crypto-radar/history.json")
OUT = Path("data/crypto-radar/outcomes.json")
HORIZONS = {"1h": 1, "4h": 4, "24h": 24}
MAX_LAG_MINUTES = 30
DIRECTIONAL = {
    "RISK-OFF": "DEFENSIVE",
    "PANIC": "DEFENSIVE",
    "DISTRIBUTION": "DEFENSIVE",
    "RISK-ON": "RISK_ON",
}


def parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def pct_return(p0, p1):
    if not isinstance(p0, (int, float)) or not isinstance(p1, (int, float)) or p0 <= 0:
        return None
    return round((p1 / p0 - 1) * 100, 4)


def classify(regime: str, ret):
    direction = DIRECTIONAL.get(regime)
    if direction is None or ret is None:
        return None
    if direction == "DEFENSIVE":
        return "ALIGNED" if ret <= 0 else "NOT_ALIGNED"
    return "ALIGNED" if ret >= 0 else "NOT_ALIGNED"


def main():
    h = json.loads(HISTORY.read_text(encoding="utf-8"))
    records = [x for x in h.get("records", []) if isinstance(x, dict) and x.get("generated_at")]
    records.sort(key=lambda x: x["generated_at"])

    # Only confirmed, quality-ready regimes can create an evaluation event.
    events = []
    prev_confirmed = None
    for i, x in enumerate(records):
        regime = x.get("regime")
        if not x.get("quality_ready") or not x.get("regime_confirmed") or not regime:
            continue
        if prev_confirmed is None:
            prev_confirmed = regime  # baseline, not a transition
            continue
        if regime != prev_confirmed:
            events.append({
                "index": i,
                "generated_at": x["generated_at"],
                "from_regime": prev_confirmed,
                "to_regime": regime,
                "btc_price_at_transition": x.get("btc_price"),
                "investor_action": x.get("investor_action"),
                "trader_action": x.get("trader_action"),
            })
            prev_confirmed = regime

    for e in events:
        t0 = parse_ts(e["generated_at"])
        p0 = e.get("btc_price_at_transition")
        e["outcomes"] = {}
        for label, hours in HORIZONS.items():
            target = t0 + timedelta(hours=hours)
            cutoff = target + timedelta(minutes=MAX_LAG_MINUTES)
            match = None
            for x in records[e["index"] + 1:]:
                tx = parse_ts(x["generated_at"])
                if tx < target:
                    continue
                if tx > cutoff:
                    break
                if isinstance(x.get("btc_price"), (int, float)):
                    match = x
                    break
            ret = pct_return(p0, match.get("btc_price") if match else None)
            e["outcomes"][label] = {
                "status": "CLOSED" if match else "OPEN",
                "observed_at": match.get("generated_at") if match else None,
                "btc_price": match.get("btc_price") if match else None,
                "btc_return_pct": ret,
                "alignment": classify(e["to_regime"], ret),
            }
        e.pop("index", None)

    summary = {}
    for label in HORIZONS:
        closed = []
        aligned = 0
        directional = 0
        for e in events:
            o = e["outcomes"][label]
            if o["status"] == "CLOSED" and o["btc_return_pct"] is not None:
                closed.append(o["btc_return_pct"])
            if o.get("alignment") is not None:
                directional += 1
                if o["alignment"] == "ALIGNED":
                    aligned += 1
        summary[label] = {
            "closed": len(closed),
            "open": len(events) - len(closed),
            "avg_btc_return_pct": round(sum(closed) / len(closed), 4) if closed else None,
            "positive_rate_pct": round(100 * sum(1 for r in closed if r > 0) / len(closed), 1) if closed else None,
            "negative_rate_pct": round(100 * sum(1 for r in closed if r < 0) / len(closed), 1) if closed else None,
            "directional_cases": directional,
            "alignment_rate_pct": round(100 * aligned / directional, 1) if directional else None,
        }

    closed24 = summary["24h"]["closed"]
    sample_quality = "WARMUP" if closed24 < 3 else "PRELIMINARY" if closed24 < 10 else "USABLE"
    out = {
        "version": "1.6.2",
        "method": "confirmed regime transitions; forward BTC observation at 1h/4h/24h; no lookahead",
        "max_observation_lag_minutes": MAX_LAG_MINUTES,
        "event_count": len(events),
        "sample_quality": sample_quality,
        "summary": summary,
        "events": events,
        "notes": [
            "Outcome validation measures post-transition BTC behavior; it is not a crash probability model.",
            "First confirmed regime is baseline and is never counted as a transition.",
            "Directional alignment is informational and does not change Risk/Regime thresholds automatically.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"events": len(events), "closed_24h": closed24, "sample_quality": sample_quality}, ensure_ascii=False))


if __name__ == "__main__":
    main()
