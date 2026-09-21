# TA Market Monitor — Release History

## R0.6 SAFE SIGNAL — PASS
Introduced closed/fresh candle gate, directional structure, price trigger, RVOL, structural invalidation, market-derived targets, R/R and WAIT/READY/INVALID semantics.

## R0.6.2 Live Data — PASS
Moved production data flow away from browser->MOEX to GitHub Actions -> MOEX ISS -> static JSON -> Pages.

## R0.7 Simple Market Context — PASS
Added IMOEX regime, TQBR breadth, CNY/RUB and active Brent contract. Mixed/N/A context does not invent a veto. Event Risk remains N/A until a reliable calendar exists.

## R0.8 Production — PASS
Added production validation, persistence, signal history, Telegram READY alerts, snapshot freshness protection and execution-risk/position-sizing support.

## R0.9 Production Observation — PASS
Added READY outcome evaluator and model-quality metrics.

## R0.9.2 Sample Quality Gate — PASS
Locked evidence thresholds: <10 INSUFFICIENT, 10-29 PRELIMINARY, >=30 USABLE.

## R0.9.2.1/2 Public health hardening — PASS
Cache-busted Pages verification and aligned public safety marker.

## R0.9.2.3 Freshness Determinism — DEPLOYED
Signal-history candle freshness is anchored to snapshot.generated_at so runner delay cannot change the state of the same persisted snapshot. Trading thresholds were not changed.

## Next: R0.9.2.4 Documentation & Session State Alignment
Canonicalize project documents and distinguish MARKET CLOSED / LAST SESSION from true stale-data failure. No trading-model changes are authorized.
