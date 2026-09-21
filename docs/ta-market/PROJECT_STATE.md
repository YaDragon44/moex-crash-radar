# TA Market Monitor — Project State

Updated: 2026-09-21
Canonical repository: YaDragon44/moex-crash-radar

## Current state
- Release: R0.9.2.3
- Phase: PRODUCTION OBSERVATION
- Production: GREEN
- Trading model: FROZEN
- Scope: SBERP, VKCO, OZPH; D1, H1, M10
- Runtime source: MOEX ISS
- Pipeline: GitHub Actions -> MOEX ISS -> static JSON -> GitHub Pages -> browser
- Signal states: READY / WAIT / INVALID
- Performance definition: WIN if TP2 before Stop after READY; LOSS if Stop first; AMBIGUOUS if both occur in one candle; OPEN otherwise.
- Sample gate: <10 closed = INSUFFICIENT; 10-29 = PRELIMINARY; >=30 = USABLE.
- Current evidence at audit: 0 READY, 0 closed, Sample Quality INSUFFICIENT.

## Governance lock
Do not tune trading thresholds from the current insufficient sample. Safety thresholds, scoring and target/stop logic remain frozen until the evidence gate permits review.

## Known limitations
- Reliable macro/corporate Event Risk calendar is not integrated; status remains N/A.
- Broker short availability is not verified.
- VSA/Wyckoff/Elliott remain supporting heuristics, not independent production engines.
- Session-aware distinction between stale market data and market-closed/last-session state remains an operational UX item.

## Next task
R0.9.2.4 Documentation & Session State Alignment:
1. keep model logic unchanged;
2. align canonical documentation and release metadata;
3. distinguish MARKET CLOSED / LAST SESSION from true stale-data failure without weakening READY gates;
4. regression + public production gates;
5. return to OBSERVE.

## Evidence gates
- 10 closed READY: first preliminary model review.
- 30 closed READY: usable model review.
