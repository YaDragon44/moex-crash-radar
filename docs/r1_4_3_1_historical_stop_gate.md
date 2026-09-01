# R1.4.3.1 — Historical Stop Gate

Status: FIRST GATE PASS / STOP NOT YET VALIDATED

Goal: empirically compare four simple stop candidates for existing R1.4.2 Trend + Trigger entries without changing entry semantics.

Candidates:
- SIGNAL_CANDLE
- ATR_1_0 (Wilder ATR14)
- ATR_1_5 (Wilder ATR14)
- SWING_3

Validation period: 2026-06-01 → 2026-09-01, current public U6 contracts / SLVRUBF where applicable, 8 hourly bars after next-bar-open entry.

## Aggregate result

Signals: **1,342**

| Stop | Mean risk, bps | Stop hit % | Mean 8H exit, bps | Median 8H exit, bps | Positive % |
|---|---:|---:|---:|---:|---:|
| SIGNAL_CANDLE | 60.15 | 60.95 | 13.81 | -13.04 | 33.16 |
| ATR_1_0 | 62.92 | 51.86 | 16.99 | -24.99 | 41.06 |
| ATR_1_5 | 94.38 | 38.30 | 20.38 | -3.23 | 48.73 |
| SWING_3 | 112.07 | 40.39 | 20.53 | -5.79 | 46.13 |

## Interpretation

1. Narrow stops are hit too frequently: signal-candle 60.95%, ATR 1.0 51.86%.
2. ATR 1.5 and Swing-3 preserve substantially more trades and produce the strongest aggregate mean 8H outcome in this first gate.
3. Swing-3 is marginally better on mean outcome but requires materially wider average risk (112.07 bps vs 94.38 bps for ATR 1.5).
4. ATR 1.5 therefore remains the preferred simple **provisional risk reference** for the MVT.
5. This is NOT a validated production stop: aggregate medians remain negative and positive-outcome rate is below 50% for every candidate.
6. NG remains problematic: its best stop candidate still had a negative mean 8H result in this run.

## Decision

**MVT ATR 1.5 reference: KEEP PROVISIONALLY.**

**Hard production stop rule: NO-GO YET.**

Next gate must add chronology stability, broader roll-chain history, no-stop forward baseline, MAE/MFE normalization, realistic costs where available, and instrument-specific robustness. Do not optimize per instrument from this single 3-month current-contract sample.
