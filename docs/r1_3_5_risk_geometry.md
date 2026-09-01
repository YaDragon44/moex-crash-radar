# R1.3.5 — Risk Geometry Redesign & Candidate Preservation Test

## Goal
R1.3.4 showed that accepted-trade scarcity survives a multi-year roll-chain and broad threshold sensitivity. R1.3.5 therefore freezes the signal stack and changes the *risk geometry*, not the thresholds.

Frozen signal stack:
- 4H regime
- 1H closed-bar trigger
- M1 location
- M5 same-hour RVOL
- baseline Max Stop = 1.5 ATR
- baseline Min R/R = 2.0

FUTOI/OI M2/M3/M4 remains out of scope until authenticated history is available.

## Geometries
1. **CONTROL** — structural swing stop + nearest recent 1H obstacle. This is the R1.3.3/R1.3.4 reference.
2. **ATR_INVALIDATION** — fixed 1.25 ATR execution stop; structural swing remains an invalidation sanity check but is not the stop anchor.
3. **HTF_LIQUIDITY** — structural stop retained, but the obstacle test uses completed 4H liquidity blocks instead of every recent 1H high/low.
4. **TIME_INVALIDATION** — structural stop retained and the initial nearest-obstacle R/R veto is removed; trade still targets 2R and exits on the existing time stop when neither stop nor target is hit.

These are deliberately a small set of conceptual alternatives. There is no new best-parameter search in this release.

## Candidate preservation
For each family/model/geometry:
`preservation = accepted non-overlapping trades / pre-risk candidates`.

More trades alone is not a success condition.

## Validation
Same historical framework as R1.3.4:
- period: 2024-01-01 through 2026-08-31
- families: MX / SI / SR / GZ / LK
- deterministic quarterly roll-chain
- 60% IS / 20% Validation / 20% OOS
- no cross-contract feature or trade leakage
- contract-specific MINSTEP/STEPPRICE costs where available; otherwise gross result with explicit coverage.

## Gate
For a family/model pair where CONTROL has trades, a redesigned geometry qualifies only when:
1. accepted trades are at least 2× CONTROL;
2. expectancy is no worse than CONTROL by more than 0.10R;
3. max drawdown is no worse than CONTROL by more than 2R.

If CONTROL has zero OOS trades, relative expectancy is undefined. Such a pair is handled fail-closed: the redesign must independently produce at least 5 OOS trades, positive expectancy and max drawdown no worse than -2R.

Research GO requires at least 8 **distinct** qualifying OOS family/model pairs across the 15 possible pairs. Multiple winning geometries on the same family/model count once. This intentionally requires cross-market breadth rather than one attractive example.

## Interpretation
- If preservation rises but expectancy collapses: reject.
- If only IS improves: reject as regime-specific/overfit.
- If one family improves: do not universalize the geometry.
- If TIME_INVALIDATION wins broadly, the old obstacle veto is likely structurally over-restrictive.
- If HTF_LIQUIDITY wins broadly, obstacle resolution rather than stop width is the likely issue.
- If ATR_INVALIDATION wins broadly, structural stop anchoring is the likely issue.
- If none qualify, the bottleneck is probably upstream in signal construction rather than just risk geometry.

## Final Gate
Pending empirical GitHub Actions replay. Do not approve for trading until the measured report is attached and this section is updated.
