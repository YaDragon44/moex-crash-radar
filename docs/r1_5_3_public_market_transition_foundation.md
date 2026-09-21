# R1.5.3 — Public Market-Transition Evidence Foundation

**Status:** AUTHORIZED RESEARCH FOUNDATION / PRODUCTION NO-GO  
**Owner:** `YaDragon44/moex-crash-radar`  
**Scope:** public, historically reproducible market-internals evidence only

## Purpose

Test whether independent public market-internal observations add reproducible early context before a deterioration becomes obvious in IMOEX price. The target is evidence about a transition, not a forecast, probability, trade or portfolio instruction.

`PRICE → BREADTH → VOLUME → VOLATILITY → RESEARCH DIVERGENCE → HISTORICAL EVIDENCE → GO/NO-GO`

R1.5.3 is independent of the authenticated OI/FUTOI path. R1.5.2 remains an optional future enhancement and its `BLOCKED_AUTH` status must not prevent public-data research.

## Locks

- no new service, database, collector, ML model, score, trading signal or dashboard;
- no change to validated Crash Score, Crash State, EXIT Gate or existing source actions;
- `FACT ≠ ANALYSIS ≠ DECISION`;
- missing, stale or ambiguous data remains `N/A` / `UNKNOWN`;
- all output must retain source, event time, availability time, decision time, quality and coverage;
- a candidate must pass historical evidence before it can be projected into RADAR Market.

## Candidate FACT groups

| Group | Required observation | Boundary |
|---|---|---|
| Price | IMOEX return/trend sufficient to classify `RESILIENT`, `FALLING` or `N/A` | no price forecast |
| Breadth | reproducible constituent participation and coverage | missing coverage is not neutral |
| Volume | participation relative to its own locked historical baseline | low volume alone is not bearish |
| Volatility | realized market instability relative to its own locked historical baseline | volatility alone is not directional |

## Permitted research label

`DISTRIBUTION_WATCH` may be observed only when all usable evidence is present:

`PRICE_RESILIENT AND BREADTH_DETERIORATING AND (VOLUME_WEAKENING OR VOLATILITY_RISING)`

Otherwise the result is `NOT_OBSERVED` or `INSUFFICIENT_DATA`. This label is analysis only: it is neither a Crash State nor an investor/trader action.

## Quality contract

For every source row:

- `event_time ≤ available_time ≤ decision_time`;
- quality is `LIVE`, `DELAYED`, `STALE`, `ERROR` or `N/A`;
- no forward-fill of breadth or fabricated constituent history;
- stale/N/A input cannot fulfil a confirmation;
- exact coverage and missing-data reason are published.

## Preregistered validation

Before thresholds are chosen, lock:

1. historical period and data sources;
2. transition/drawdown outcome definition and horizons;
3. controls and ablation sequence:
   - M0: price only;
   - M1: price + breadth;
   - M2: price + breadth + volume;
   - M3: price + breadth + volatility;
   - M4: price + breadth + volume + volatility.

Report sample size, coverage, missing periods, failures and uncertainty. Metrics: Early Warning Lead Time, False Alarm Rate, Precision, Recall, persistence and incremental contribution versus M0. Preserve point-in-time availability; no look-ahead.

## Acceptance and next gate

R1.5.3 Foundation is PASS only when public historical data feasibility and deterministic feature definitions are demonstrated with tests and a preregistered evidence plan. It does **not** authorize production publication.

R1.5.3-A has now locked public-data feasibility, event labels and deterministic feature definitions. The next authorized task is **R1.5.3-B — locked public historical replay and evidence report**. It must end `PASS`, `FAIL` or `INCONCLUSIVE`; only PASS with incremental evidence may request an owner decision for source projection into RADAR.
