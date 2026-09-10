# R1.4.6.3 — Trend / Market Eligibility Diagnostic

## Why
R1.4.6.1 rejected breakout/hold/retest LONG entries. R1.4.6.2 rejected EMA20 pullback/reclaim LONG entries. Repeated trigger redesign is stopped.

## Objective
Test whether the existing EMA20/EMA50 trend state itself has useful directional forward expectancy, before any trigger, stop or exit-management logic. Determine which markets/directions are eligible for further research.

## Frozen state
At each completed 1H bar:
LONG STATE = EMA20 > EMA50, EMA20 rising, close > EMA20.
SHORT STATE = EMA20 < EMA50, EMA20 falling, close < EMA20.
No breakout/pullback trigger. No ATR stop. No RSI/RVOL/OI/FUTOI. No parameter grid.

## Forward horizons
Measure close-to-future-close directional return at +1H, +2H, +4H and +8H. Apply 0 and 5 bps round-trip research cost views. Signals are sampled only on transition into the directional state (previous bar was not the same state) to reduce serial duplication.

## Required cuts
IS / Validation / OOS; LONG vs SHORT; family; horizon; family x direction. Report n, mean, median, positive rate and profit factor proxy from positive/negative forward returns.

## Eligibility classification
For each family/direction:
- ELIGIBLE_CANDIDATE: Validation mean after 5 bps > 0 AND OOS mean after 5 bps > 0 AND OOS PF > 1 AND OOS n >= 30.
- RESEARCH_ONLY: mixed Validation/OOS or insufficient sample.
- INELIGIBLE: Validation and OOS both <= 0 with adequate sample.

This is a research eligibility gate, not a trading strategy and not a production action signal.

## Decision
If the raw trend state has no broad directional continuation edge, stop optimizing entries around EMA20/50 and redesign the Trend/Regime layer. If only selected markets/directions are eligible, future entry research is restricted to those cells; do not force one universal formula across markets.
