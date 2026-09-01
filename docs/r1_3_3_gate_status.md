# R1.3.3 — Public Baseline Backtest M0/M1/M5

Status: IMPLEMENTATION READY / HISTORICAL EVIDENCE PENDING CI RUN

Purpose: establish the public-data benchmark before adding FUTOI, so the incremental value of intraday OI / Legal / Retail can be measured honestly.

## Models
- M0 — Price Structure only.
- M1 — M0 + Location gate.
- M5 — M1 + RVOL participation gate.

No OI, FUTOI, Legal/Retail positioning, sentiment, news, ML or total score is used in this release.

## Research safeguards
- Signals use closed 1H bars only.
- Entry is evaluated on the next bar, never on the signal bar close.
- Range-complete MOEX ISS pagination is required; a partial first page is not accepted as a historical sample.
- Costs and slippage are included explicitly in R-multiple results.
- A research NO-GO caused by insufficient trades is reported as data/sample insufficiency, not as an infrastructure error.
- Results are reported separately by concrete futures contract/family; there is no hidden continuous-contract stitching.

## Baseline acceptance
The release itself passes only when code/regression CI is green and the public historical runner completes without source/infrastructure errors.

Strategy viability is a separate research gate. It requires a sufficiently large chronological sample and is not inferred from unit tests.

Candidate strategy thresholds remain research hypotheses:
- OOS PF > 1.3
- expectancy > 0.15R/trade
- acceptable max drawdown
- robustness across instruments / periods
- survival after costs/slippage

## Interpretation
R1.3.3 is not intended to prove the final OI Flow strategy. Its purpose is to create the benchmark that M2/M3/M4/FULL must beat once FUTOI access becomes available.
