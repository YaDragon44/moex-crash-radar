# R1.4.5 — Complete Historical Backtest v2

## Goal
Answer one question without adding rescue indicators: does the frozen Simple Entry Radar technical core retain a durable trading edge after costs, drawdown and out-of-sample validation?

## Frozen baseline
- Timeframe: 1H.
- Trend LONG: EMA20 > EMA50, EMA20 rising, close > EMA20.
- Trend SHORT: EMA20 < EMA50, EMA20 falling, close < EMA20.
- Trigger LONG: completed 1H close > previous completed 1H high.
- Trigger SHORT: completed 1H close < previous completed 1H low.
- Historical execution: next completed 1H bar open.
- ATR: Wilder ATR14 known at signal close.
- Protective risk reference: 1.5 × ATR14 from entry.
- Baseline exit: fixed 8 completed 1H bars, unless protective stop is hit first.
- No RSI, RVOL, OI or FIZ/YUR filters in baseline.
- No parameter optimization during the primary test.

## Historical data
Target chronology: 2024-01-01 through 2026-09-01 where public MOEX data allows.

Use historical futures contract generations rather than current-contract-only replay. Build a family roll-chain from actual contract metadata. Every trade belongs to one real contract; no synthetic price adjustment is used for entry/stop/exit execution.

Rules:
1. Discover historical contracts by family.
2. Retain only contracts whose trade dates overlap the requested chronology.
3. Prefer the nearest non-expired active generation under an explicit deterministic roll rule.
4. Never use future volume/open-interest information to decide the active contract.
5. Do not carry a position across contract roll/expiry in the baseline; force time/roll exit before the chain switches.
6. Log coverage gaps and failed contracts; never forward-fill across missing contracts.

## Chronology split
Primary split, fixed before results are inspected:
- IS: 2024-01-01 → 2024-12-31
- Validation: 2025-01-01 → 2025-12-31
- OOS: 2026-01-01 → 2026-09-01

If a family lacks sufficient early history, it is reported as INSUFFICIENT_DATA rather than silently moved into another split.

## Trade ledger
Persist one row per trade with at least:
- family / contract / side
- signal_time / entry_time / exit_time
- signal close / trigger level / entry / stop / exit
- ATR14 at signal
- exit reason: STOP / TIME / ROLL / DATA_NA
- gross bps / net bps under each cost scenario
- MAE / MFE in bps and ATR units
- holding bars
- chronology split

## Cost scenarios
Primary decision scenario: 5 bps round-trip sensitivity.
Also report 0, 2 and 10 bps. Where reliable contract-specific cost data are unavailable, keep the analysis explicitly sensitivity-based rather than fabricating precision.

## Metrics
Aggregate and per market/split:
- trades
- mean and median net trade
- positive trade rate
- gross profit / gross loss and Profit Factor
- cumulative net bps
- maximum closed-trade equity drawdown
- recovery factor
- average holding time
- stop-hit rate
- MAE/MFE distributions
- LONG vs SHORT stability
- quarter-by-quarter stability
- instrument contribution concentration

## Robustness checks
These are sensitivity checks, not parameter selection:
- cost: 0 / 2 / 5 / 10 bps
- ATR stop: 1.0 / 1.5 / 2.0
- time exit: 4H / 8H / 12H

The primary baseline remains ATR1.5 + 8H regardless of neighboring results. The neighborhood is used only to detect a narrow overfit peak.

## GO / NO-GO
A production-candidate baseline requires all of the following:
1. OOS net expectancy > 0 after 5 bps.
2. OOS Profit Factor > 1.0; preferred robustness zone >= 1.15.
3. Positive aggregate result is not dominated by one instrument or one quarter.
4. Meaningful proportion of instrument-quarter cells are positive; target >= 60%, preferred >= 70%.
5. Max drawdown is finite and economically tolerable relative to cumulative return; report Recovery Factor.
6. Edge does not disappear immediately under 10 bps sensitivity.
7. Parameter-neighborhood check does not show a single isolated profitable point surrounded by broad losses.
8. No look-ahead, roll-stitching or execution-semantics defects in regression tests.

Outcomes:
- GO: technical core is eligible for production-candidate hardening.
- CONDITIONAL: aggregate passes but specific markets fail; those markets become RESEARCH_ONLY / NO ENTRY pending separate evidence.
- NO-GO: OOS/cost/stability gate fails; change the core rather than stacking additional indicators.

## Special gates
- NG receives an explicit independent verdict because prior short-window evidence was negative.
- Missing OI/FUTOI is irrelevant to this baseline and must not be imputed.
- Public-data delay does not affect historical closed-bar chronology, but data-quality coverage must still be reported.

## Required tests
- closed-bar trigger has no look-ahead
- next-bar-open execution
- Wilder ATR14 chronology
- stop-hit semantics
- deterministic roll selection
- no cross-contract position leakage
- chronological split boundaries
- cost application exactly once per completed trade
- equity/drawdown accounting
- gate logic

## Release decision
R1.4.5 is a research/validation release. No live strategy rule is changed solely because of an IS result. OOS and full regression govern the decision.
