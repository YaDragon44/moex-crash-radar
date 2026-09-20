# R1.5.3 — MOEX Market Transition Foundation

## Purpose

Detect deterioration in the MOEX market regime before it becomes obvious from the index price.

This release is intentionally independent of authenticated FUTOI. R1.5.2 remains available as a parallel participant-behaviour enhancement, but BLOCKED_AUTH must not block public-market transition research.

## Hypothesis

A transition toward DISTRIBUTION should be investigated when the index remains resilient while internal market evidence deteriorates:

- IMOEX price/trend: resilient or rising;
- Breadth: deteriorating;
- Volume participation: weakening;
- Volatility: rising.

This combination is **Transition Evidence**, not a SELL signal and not a calibrated crash probability.

## Minimal architecture

DATA → QUALITY GATE → 4 MARKET FEATURES → DIVERGENCE → TRANSITION EVIDENCE → HISTORICAL VALIDATION → GO/NO-GO

No new service, database, ML model, news engine, participant-position substitute, or production trading signal is authorized.

## Feature groups

### 1. IMOEX / Price State
Measure only enough to determine whether the headline index is rising, falling or resilient.

### 2. Breadth
Use constituent participation to measure whether the move is broad or narrowing. Exact breadth metric must be chosen from historically reproducible MOEX public data. Missing constituent coverage is N/A, never neutral.

### 3. Volume Participation
Compare current market participation with its own historical baseline. Do not treat low volume as bearish by itself.

### 4. Volatility
Measure whether realized market instability is expanding or contracting. Volatility alone is not a direction signal.

## Core divergence

Candidate DISTRIBUTION_WATCH evidence requires:

PRICE_RESILIENT
AND BREADTH_DETERIORATING
AND at least one of:
- VOLUME_WEAKENING
- VOLATILITY_RISING

Stronger evidence may require both confirmations, but thresholds are hypotheses until historical validation.

No weighted composite score is authorized in this release.

## Quality Gate

Every observation must include:
- source
- event_time
- available_time
- decision_time
- quality: LIVE / DELAYED / STALE / N/A

Rules:
- available_time <= decision_time;
- no look-ahead;
- no forward-fill of missing breadth;
- no fabricated constituent history;
- stale/N/A inputs cannot satisfy a confirmation;
- output must expose coverage.

If required price or breadth evidence is unavailable, transition state is UNKNOWN rather than NEUTRAL.

## Historical validation

Validate on multiple market regimes and include both warning and non-warning periods.

Primary metrics:
1. Early Warning Lead Time
2. False Alarm Rate
3. Precision / Recall for predefined drawdown/regime-transition events
4. Signal Stability / persistence
5. Incremental value versus price-only control

Ablation:
- M0 = PRICE only
- M1 = PRICE + BREADTH
- M2 = PRICE + BREADTH + VOLUME
- M3 = PRICE + BREADTH + VOLATILITY
- M4 = PRICE + BREADTH + VOLUME + VOLATILITY

The release passes only if internal-market evidence improves transition detection versus M0 without unacceptable false alarms.

## Action lock

Until historical evidence passes:
- Investor Action: no new automated recommendation.
- Trader Action: no new automated recommendation.
- Production: NO-GO.
- Dashboard may show research evidence only, clearly labelled.

## Acceptance

R1.5.3 Foundation is complete when:
- public historical source feasibility is proven;
- point-in-time semantics are documented;
- feature definitions are deterministic;
- Quality Gate is tested;
- historical event labels are preregistered before threshold tuning;
- ablation is reproducible;
- GO/NO-GO is evidence-based.

## Current status

FOUNDATION AUTHORIZED
FUTOI DEPENDENCY: NONE
PRODUCTION: NO-GO
NEXT: Public historical data feasibility and event-label preregistration.
