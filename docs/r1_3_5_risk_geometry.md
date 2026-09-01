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
- bounded 30-day ISS history retrieval
- contract-specific MINSTEP/STEPPRICE costs where available; otherwise gross result with explicit coverage.

## Gate
For a family/model pair where CONTROL has trades, a redesigned geometry qualifies only when:
1. accepted trades are at least 2× CONTROL;
2. expectancy is no worse than CONTROL by more than 0.10R;
3. max drawdown is no worse than CONTROL by more than 2R.

If CONTROL has zero OOS trades, relative expectancy is undefined. Such a pair is handled fail-closed: the redesign must independently produce at least 5 OOS trades, positive expectancy and max drawdown no worse than -2R.

Research GO requires at least 8 **distinct** qualifying OOS family/model pairs across the 15 possible pairs. Multiple winning geometries on the same family/model count once. This intentionally requires cross-market breadth rather than one attractive example.

## Empirical result
GitHub Actions run `33531347138` completed successfully on commit `e40c3b6bc7f009aa610ac8cf11300a107ba3ea9f`. Unit regression and the full historical risk-geometry replay both passed. Artifact: `r1-3-5-risk-geometry-report` (`9810060257`).

Measured Gate: **NO-GO**. Only **6 of 15** distinct OOS family/model pairs qualified versus the required 8.

### OOS aggregate behavior
Across all five futures families and M0/M1/M5:

| Geometry | Accepted trades | Pre-risk candidates | Mean expectancy | Total R | Mean max DD |
|---|---:|---:|---:|---:|---:|
| CONTROL | 25 | 2230 | -0.0764R | -4.6997R | -1.2216R |
| ATR_INVALIDATION | 1042 | 2230 | -0.0096R | +8.5245R | -8.4077R |
| HTF_LIQUIDITY | 117 | 2230 | -0.0029R | -9.0523R | -2.5887R |
| TIME_INVALIDATION | 591 | 2230 | -0.0625R | -26.8365R | -8.3071R |

Interpretation of these aggregates must remain conservative because execution-cost coverage is incomplete for historical contracts and the average expectancy is not a portfolio-weighted statistic.

### What improved
**ATR_INVALIDATION** proves that the old structural-stop/obstacle combination is a major candidate-suppression mechanism. OOS accepted trades rise from 25 CONTROL trades to 1042. However this is not a trading approval: mean OOS expectancy remains slightly negative and drawdown expands materially. Candidate density improved much faster than risk-adjusted quality.

**HTF_LIQUIDITY** is the only redesign that passes the release qualification rule on multiple coherent family/model pairs without the extreme drawdown expansion seen in ATR/TIME variants. All six qualifying pairs are concentrated in **MX and SI**, so cross-market breadth is insufficient. SI is the strongest signal: OOS M0/M1 each produced 8 trades at +0.4129R expectancy and M5 produced 5 trades at +0.3471R, but these samples are still small.

**TIME_INVALIDATION** rejects the hypothesis that simply deleting the obstacle veto is enough. It increases trade count substantially but produces aggregate OOS -26.8365R with much larger drawdowns. The nearest-obstacle rule is over-restrictive, but some forward-path/room-to-move filter is still necessary.

### Stability across chronology
The broad patterns are not cleanly stable across IS → Validation → OOS:
- ATR_INVALIDATION: aggregate mean expectancy approximately -0.0060R / +0.0083R / -0.0096R.
- HTF_LIQUIDITY: -0.0940R / +0.0954R / -0.0029R.
- TIME_INVALIDATION: -0.0951R / +0.0648R / -0.0625R.

This sign instability is another reason for NO-GO. Validation alone would have looked encouraging and would have produced a false sense of edge.

## Investment logic conclusion
R1.3.5 changes the diagnosis from R1.3.4:

1. The original nearest-1H-obstacle geometry is indeed structurally too restrictive.
2. Removing it completely is unsafe.
3. Replacing the stop with a fixed ATR stop preserves candidates but creates unacceptable drawdown expansion and no robust positive expectancy.
4. Coarser 4H liquidity/structure is the most promising direction, particularly for MX/SI, but it is not yet broad or statistically mature enough for production trading.
5. Therefore the next research step should improve **forward-path quality / trade management**, not optimize another stop threshold.

## Final Gate
**R1.3.5 = IMPLEMENTATION PASS / RESEARCH NO-GO.**

Do not change the production trading rules from this release. The next release should test whether HTF structure plus more realistic trade management can convert the higher preserved candidate set into stable OOS quality without the drawdown explosion observed in ATR_INVALIDATION and TIME_INVALIDATION.
