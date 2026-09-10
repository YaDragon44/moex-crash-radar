# R1.4.7 — Simple Market Regime Engine Redesign

## Evidence
R1.4.5: complete roll-chain strategy NO-GO. R1.4.6: LONG is primary defect. R1.4.6.1 and .2: breakout and pullback/reclaim LONG entry families rejected. R1.4.6.3: frozen EMA20/50 directional state itself failed broad Validation/OOS eligibility; no family/direction reached ELIGIBLE_CANDIDATE.

## Objective
Redesign the layer above Entry. Detect an earlier, simpler market state/transition before optimizing any trigger. This release is a regime forward-expectancy experiment, not a trading strategy.

## Design principles
- DATA -> STATE -> TRANSITION -> RISK -> ACTION.
- Completed 1H bars only; no look-ahead.
- No entry trigger, stop, TP, sizing or trade management.
- No RSI, RVOL, OI, FUTOI, news, sentiment or ML.
- No parameter grid/search.
- Exactly three pre-specified regime hypotheses plus old EMA state as control.

## R0 — EMA CONTROL
Existing state from R1.4.6.3: LONG when EMA20>EMA50, EMA20 rising and close>EMA20; SHORT symmetric.

## R1 — PRICE STRUCTURE
Use completed-bar rolling structure only.
LONG transition: close breaks above the highest completed high of the previous 8 bars AND the lowest low of the last 4 completed bars is above the lowest low of the preceding 4 bars (rising local floor).
SHORT symmetric: close breaks below previous 8-bar low AND recent 4-bar high is below preceding 4-bar high.
This approximates HH/HL vs LH/LL without discretionary swing labeling.

## R2 — EARLY TREND TRANSITION
Use EMA20 slope and price location, but remove the late EMA20/EMA50 crossover requirement.
LONG transition: close crosses from <= EMA20 to > EMA20, EMA20 rising, and EMA20 is not materially below EMA50: EMA20/EMA50 >= 0.995.
SHORT symmetric: cross from >= EMA20 to < EMA20, EMA20 falling, EMA20/EMA50 <= 1.005.
The fixed 0.5% tolerance is a hypothesis, not an optimized threshold.

## R3 — STRUCTURE + EARLY TREND
Intersection of R1 directional structure transition and R2 directional early-trend condition on the same completed bar. This tests whether two independent simple groups improve precision without adding indicators.

## Measurement
Same historical chain/splits as current research: IS 2024, Validation 2025, OOS 2026 through available period. Directional close-to-close forward return at +1H, +2H, +4H, +8H. Primary horizon 4H. Report gross and 5 bps research-cost view, n, mean, median, positive rate, PF proxy, family breadth and quarter stability.

## Candidate gate
A regime hypothesis is CANDIDATE only if, on primary 4H after 5 bps:
- Validation mean > 0;
- OOS mean > 0;
- OOS PF > 1;
- OOS n >= 100 aggregate where available;
- >=50% of adequately sampled families positive in OOS;
- no obvious single-family concentration.
Otherwise NO-GO / RESEARCH_ONLY.

## Decision rule
If none passes, stop using EMA-derived trend as the primary regime mechanism and move to a broader market-specific Regime Engine design rather than stacking more entry filters. If one passes, validate stability before any Entry Engine work resumes.
