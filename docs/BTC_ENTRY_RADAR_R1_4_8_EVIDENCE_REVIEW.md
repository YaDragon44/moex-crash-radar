# BTC Entry Radar R1.4.8 — Evidence Accumulation & Signal Quality Review

Date: 2026-09-14

## Status

**EVIDENCE REVIEW: INSUFFICIENT POSITIVE SAMPLE**

**Model change gate: NO-GO**

No thresholds or indicators are changed in this release.

## Production evidence reviewed

- Durable production journal: 15 snapshots.
- Quality: 15/15 snapshots are `DATA READY`, coverage 100%.
- Raw positive states (`WATCH`, `ARMED`, `LONG_READY`): 0.
- Confirmed positive states: 0.
- Performance tracker: 0 signals / 0 scored signals.

## Why there are no positive signals yet

The observed period did not enter the strategy's crowd entry zone:

- F&G remained above 35 throughout the reviewed journal.
- Therefore the Crowd Gate alone prevented `WATCH`, `ARMED`, or `LONG_READY`.
- In the latest snapshots the Risk Gate also became restrictive because `stop_atr > 2`.
- OI is currently `STABLE` and is not the blocker.
- Hysteresis has not yet had a positive transition to confirm, so its false-transition reduction and lead-time cost cannot yet be measured.

## Investment logic review

This is expected behavior for a fear-entry system. Absence of trades during neutral/greed conditions is not evidence that the strategy is broken. Relaxing the F&G or risk thresholds because no trades occurred would contaminate the forward test and create selection bias.

Current interpretation:

`NO SIGNAL` is a valid output.

## Decision

**KEEP R1.4.7 production rules unchanged.**

Do not add RSI, EMA, Funding, Long/Short, new scores, or threshold tuning at this stage.

## Evidence gate for next review

Re-open signal-quality evaluation only after at least one of these conditions is met:

1. at least 10 raw positive-state observations are collected, or
2. at least 5 confirmed positive-state transitions are collected, or
3. a critical data/logic defect is found.

Stronger strategy claims still require a materially larger sample (target 30–50 positive signals).

## Next step

Continue production collection and compare raw vs confirmed transitions once positive states occur. Measure:

- false raw transitions suppressed by hysteresis;
- confirmation delay / lead-time cost;
- MAE/MFE and 24h/72h/7d outcomes;
- whether confirmed signals improve stability without destroying useful early warning.

Until then: **OBSERVE → COLLECT EVIDENCE → VALIDATE**.
