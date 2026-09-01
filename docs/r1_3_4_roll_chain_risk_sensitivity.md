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

## Interpretation rules
- High trade density alone is not success.
- Positive IS plus weak OOS is overfit / regime-specific, not edge.
- One profitable family is not enough for a universal risk-gate change.
- Relaxing 1.5 ATR or 2R is allowed only if a broad neighboring parameter region is stable out of sample.
- The release tests the public price/location/RVOL baseline only; it does not make claims about OI or participant positioning.

## Empirical result
Pending the R1.3.4 GitHub Actions historical replay artifact. The final Gate section must be updated from measured data before release closure.
