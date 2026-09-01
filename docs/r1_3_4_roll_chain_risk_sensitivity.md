# R1.3.4 — Historical Roll-Chain & Risk-Gate Sensitivity Validation

## Research question
R1.3.3 produced 598 Regime+Trigger candidates but almost no accepted trades. The dominant rejection sources were Stop Geometry and nearest-obstacle R/R. R1.3.4 tests whether that scarcity is a short-sample artifact or a structural property of the risk gate.

This release does **not** optimize parameters for the best historical result.

## Public models
- M0 — 4H Regime + closed 1H Trigger
- M1 — M0 + Location
- M5 — M1 + same-hour RVOL

FUTOI/OI M2/M3/M4 remains blocked until authenticated historical access exists.

## Roll-chain policy
Quarterly contract identifiers are generated explicitly for MX, Si, SR, GZ and LK using H/M/U/Z month codes. A calendar roll is applied five business days before the third-Thursday expiry proxy.

Safety rules:
1. Every bar retains the concrete source SECID.
2. Missing active-contract bars are not backfilled from another maturity.
3. Features and trades reset at each contract boundary.
4. No synthetic price adjustment is applied, so no trade may bridge a roll gap.
5. Missing contracts are reported rather than silently skipped from the quality diagnostics.

## Execution-cost policy
The old common quote-bps proxy is disabled in R1.3.4. Where MOEX ISS exposes contract metadata, cost geometry uses:
- MINSTEP
- STEPPRICE
- configurable round-trip slippage in ticks
- configurable broker fee in RUB per round trip

Risk RUB = `abs(entry - stop) * STEPPRICE / MINSTEP`.

Execution cost R = `(broker fee RUB + slippage ticks * STEPPRICE) / risk RUB`.

If historical contract metadata is unavailable, the result stays gross for that contract and cost coverage is shown explicitly. No fabricated fee/tick assumptions are permitted.

## Sensitivity grid
Broad grid only:
- Max Stop ATR: 1.25 / 1.50 / 1.75 / 2.00
- Minimum obstacle R/R: 1.50 / 1.75 / 2.00 / 2.25

A single best cell is explicitly non-actionable.

## Validation
Chronological split:
- IS 60%
- Validation 20%
- OOS 20%

A model has a candidate stable positive plateau only when at least 60% of its grid cells have positive expectancy with at least 30 trades per cell. The family must retain a broad positive plateau in both Validation and OOS.

Research GO requires this behavior across a majority of measurable futures families. Otherwise the release is NO-GO and the baseline risk gate remains unapproved for trading.

## Empirical replay
GitHub Actions run `33528645460` completed successfully. Artifact: `r1-3-4-roll-chain-risk-sensitivity-report`, artifact id `9809014273`.

Period: 2024-01-01 through 2026-08-31.

Coverage:
- MX: 11,534 1H bars / 11 quarterly contracts
- SI: 10,820 1H bars / 11 quarterly contracts
- SR: 11,509 1H bars / 11 quarterly contracts
- GZ: 11,478 1H bars / 11 quarterly contracts
- LK: 11,181 1H bars / 11 quarterly contracts
- total: 56,522 1H bars / 55 concrete contract segments
- missing planned active contracts: 0 in the measured chain

The expanded sample confirms that R1.3.3 scarcity was not merely a one-quarter accident.

Across all 240 IS grid cells (5 families × 3 models × 16 parameter pairs), the maximum accepted trade count in any single cell was only 18; median was 6. No IS cell reached the required 30-trade evidence threshold.

Validation was even thinner: maximum 2 trades per grid cell, median 0. OOS: maximum 7, median 2. Therefore no model/family could form a statistically usable positive plateau.

Examples at the original baseline risk geometry `Max Stop = 1.5 ATR / Min R/R = 2.0`:
- MX M0: IS 10 trades, +0.3173R expectancy; Validation 1, +0.1181R; OOS 3, -0.5068R.
- SI M0: IS 0; Validation 0; OOS 3, -0.0023R.
- SR M0: IS 11, -0.3465R; Validation 0; OOS 0.
- GZ M0: IS 6, +0.1317R; Validation 0; OOS 2, -0.7804R.
- LK M0: IS 4, -1.0000R; Validation 1, +2.0000R; OOS 2, +0.5000R.

These values are descriptive only. The samples are too small to establish edge.

Even at the most permissive tested boundary (`Max Stop = 2.0 ATR / Min R/R = 1.5`), accepted trade counts remain too low to support a robust plateau decision. This is evidence that the current combination of structural stop construction plus nearest-obstacle filter is structurally restrictive, not simply that 1.5 ATR / 2R was slightly too strict.

## Cost quality gate
Contract-specific cost logic is implemented and the invalid common quote-bps model is removed from this release. However MOEX ISS provided usable MINSTEP/STEPPRICE coverage for only 9.09% of the concrete contracts used in each family during this historical replay.

Therefore the empirical metrics are predominantly **gross**, not execution-ready net results. This is an additional independent reason not to approve a strategy GO. Historical contract economics must be sourced more completely before final trading validation.

## Final Gate
**R1.3.4 = IMPLEMENTATION PASS / RESEARCH NO-GO**

PASS:
- deterministic multi-year quarterly roll-chain
- 55 concrete contract segments with provenance
- no cross-contract trade leakage
- broad non-optimized sensitivity grid
- chronological IS / Validation / OOS
- contract-specific tick-based execution-cost engine
- full unit regression
- public MOEX empirical replay

NO-GO:
- zero positive plateaus meeting the minimum sample rule
- accepted-trade density remains extremely low across the whole sensitivity surface
- original 1.5 ATR / 2R setting does not survive OOS consistently
- relaxing to 2.0 ATR / 1.5R still does not create adequate evidence density
- historical execution-cost coverage only 9.09%
- no evidence yet that M0/M1/M5 provides a stable tradable edge

## Investment / trading logic conclusion
Do **not** loosen the risk thresholds mechanically and do **not** deploy the public baseline as a trading system.

The next research step should redesign the **risk geometry itself**, not optimize its numeric thresholds. In particular, test whether the nearest-obstacle rule and structural-stop definition are eliminating valid setups because they are too literal for 1H futures microstructure.

Recommended next release: **R1.3.5 — Risk Geometry Redesign & Candidate Preservation Test**.

R1.3.5 should keep Regime/Trigger/Location/RVOL frozen and compare a small number of conceptually different risk constructions, for example:
1. current structural swing stop + nearest obstacle (control);
2. ATR-normalized stop with structure as invalidation confirmation;
3. structural stop but target/obstacle evaluated on higher-timeframe liquidity zones rather than every recent 1H high/low;
4. optional time-based invalidation independent from initial R/R.

The Gate should ask whether candidate preservation improves materially **without** degrading OOS expectancy / drawdown stability. If the redesigned geometry only creates more trades but worse quality, reject it.

## Interpretation rules
- High trade density alone is not success.
- Positive IS plus weak OOS is overfit / regime-specific, not edge.
- One profitable family is not enough for a universal risk-gate change.
- A single profitable sensitivity cell is not a plateau.
- Threshold relaxation is not allowed as a substitute for structural redesign.
- The release tests the public price/location/RVOL baseline only; it does not make claims about OI or participant positioning.
