# R1.4.8.1 — EQUITY SHORT Robustness Gate

## Objective
Validate the only two segments that passed R1.4.8 eligibility: EQUITY SHORT with R0_EMA_CONTROL and R2_EARLY_TREND. No new indicators, no threshold tuning, no horizon optimization.

## Frozen universe
SBER, GAZP, ROSN, T only. SHORT only.

## Frozen models
- R0_EMA_CONTROL
- R2_EARLY_TREND

Definitions are inherited unchanged from R1.4.7/R1.4.8.

## Chronology and measurement
- public MOEX historical roll-chain, fail-closed
- period 2022-01-01 through 2026-09-01 where available
- Development: 2022-2024
- Validation: 2025
- OOS: 2026
- primary horizon: 4H
- diagnostics: 1H, 2H, 8H
- cost sensitivity: 0 / 2 / 5 / 10 bps
- completed bars only; same-contract forward horizon; no forward-fill

## Required robustness checks
For each model and each family:
- n, mean, median, positive rate, profit factor
- Development / Validation / OOS
- year and half-year stability
- leave-one-family-out
- leave-best-event-out
- top-1 and top-3 positive PnL concentration
- cost sensitivity at 0/2/5/10 bps

## Gate
A model may remain RESEARCH_CANDIDATE only if at 5 bps:
1. Validation mean > 0 and PF > 1;
2. OOS mean > 0 and PF > 1;
3. OOS n >= 20 preferred, >= 15 minimum;
4. at least 2 of 4 families have positive OOS mean;
5. leave-best-event OOS mean remains > 0;
6. leave-one-family-out OOS mean remains > 0 for every represented family;
7. no family contributes more than 60% of positive OOS PnL;
8. OOS remains non-negative at 10 bps costs;
9. positive evidence is not confined to one single chronological subperiod when more than one is available.

Any failure => REJECTED_NON_ROBUST or INSUFFICIENT_EVIDENCE.

## Release decision
This is research only. Production remains NO-GO regardless of outcome. If both models fail, stop technical-only regime research and move to independent information groups: OI, FIZ/YUR positioning, and Context. If one survives, proceed to an independent market-specific validation gate before any live trading use.
