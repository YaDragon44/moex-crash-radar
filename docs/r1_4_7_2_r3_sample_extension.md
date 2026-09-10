# R1.4.7.2 — R3 Sample Extension & Market-Specific Validation

## Evidence
R1.4.7.1 kept frozen R3 as RESEARCH_CANDIDATE: Validation +1.36 bps (n=29), OOS +17.51 bps (n=15), PF 1.818. Removing the best OOS event leaves +6.85 bps / PF 1.298. Top-1 positive P&L share 28.56%; top-3 share 70.66%. Five of nine represented OOS families and both OOS quarters contributed positive evidence. Production remains NO-GO.

## Objective
Increase independent evidence without changing R3. Determine whether the effect is repeatable across a longer chronology and market-specific cells.

## Frozen R3
Exactly R1.4.7/R1.4.7.1 Structure + Early Transition. No rule, threshold, horizon or cost tuning.

## Data extension
Attempt MOEX public historical roll-chain from 2022-01-01 through 2026-09-01 for the currently supported 11 families. Missing contracts/data are fail-closed and reported as N/A. Do not fabricate continuity or forward-fill across contracts. Preserve completed-bar semantics.

## Chronology
Development history: 2022-2024; Validation: 2025; OOS: 2026 through available period. In addition report calendar-year and half-year cells to expose regime concentration.

## Primary measurement
4H directional forward return after 5 bps. Also retain 1H/2H/8H as diagnostics. Report n, mean, median, positive rate, PF, trimmed mean, family/year/half-year/side cuts, event concentration and leave-one-family-out.

## Market-specific classification
For each family/direction, classify:
- SUPPORTIVE: Validation and OOS mean >0, OOS PF>1, with at least 10 OOS events (30 preferred).
- MIXED: signs conflict or sample insufficient.
- NEGATIVE: Validation and OOS <=0 with at least 10 OOS events.
No market-specific trading rule is created here.

## Research gate
R3 remains RESEARCH_CANDIDATE only if aggregate Validation and OOS remain >0 after 5 bps, OOS PF>1, evidence spans >=2 families and >=2 chronological subperiods, and leave-one-best-event / leave-one-family checks do not reverse the aggregate sign. Promotion to production is forbidden in this release.
