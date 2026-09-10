# R1.4.8 — Market-Specific Regime Segmentation

## Why
R1.4.5–R1.4.7.2 rejected the assumption that one universal 1H trend/regime rule is reliable across the MOEX futures universe. R3 remained positive in aggregate but failed the extended robustness gate: Development +1.26 bps/PF 1.037, Validation +1.36/PF 1.054, OOS +17.51/PF 1.818 with only 15 events; no market×direction cell had adequate support and evidence did not span two positive OOS half-years.

## Objective
Stop searching for a universal signal. Test whether simple regime behavior is market-class and direction specific before any new Entry Engine work.

## Frozen universe / segmentation
Use only existing historically mapped families. No new indicator optimization.
- INDEX: MX, MMU
- FX: SI, CRU
- EQUITY: SBER, GAZP, ROSN, T
- COMMODITY: GD, SVU, NG
BR and separate SLVRUBF remain N/A until historical chain support is implemented.

Analyze LONG and SHORT independently. Never combine directions to hide asymmetry.

## Candidate state families
Reuse existing evidence only; no parameter grid:
- EMA_STATE: R0 EMA directional transition
- STRUCTURE: R1 price-structure event
- EARLY: R2 early trend transition
- STRUCTURE_EARLY: R3 intersection

These are explanatory state/transition hypotheses, not trade entries.

## Measurement
Completed 1H bars, same fail-closed historical roll-chain and chronology. Primary forward horizon 4H after 5 bps research cost; 1H/2H/8H diagnostic. Report class×direction and family×direction: n, mean, median, positive rate, PF, yearly/half-year stability and contribution concentration.

## Eligibility
A class×direction×model is only a CANDIDATE if Validation and OOS means >0, OOS PF>1, OOS n>=30 preferred (>=15 minimum research threshold), evidence comes from >=2 families when class has >=2 mapped families, and no single family contributes >60% of positive OOS P&L. Otherwise RESEARCH_ONLY or REJECTED.

## Decision
This release does not create production trading signals. It answers only: which market classes/directions, if any, deserve a separate Regime Engine? If no segment passes, stop technical-only regime redesign and move to independent information groups (positioning/OI/context) rather than more price-indicator variants.
