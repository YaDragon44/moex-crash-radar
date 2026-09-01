# R1.3.3 — Public Baseline Backtest M0/M1/M5

Status: COMPLETE / RESEARCH NO-GO

## Objective
Measure the standalone edge and signal density of the public-data core before FUTOI is enabled.

Ablation:
- M0 = closed 4H Regime + 1H closed-bar Trigger
- M1 = M0 + Location (PDH/PDL + local 1H structure)
- M5 = M1 + same-hour RVOL

OI, Legal and Retail positioning are deliberately excluded. Their incremental value must later be measured against this baseline.

## Point-in-time rules
- Only closed 1H bars may create a signal.
- 4H regime uses only fully completed prior 4H clock buckets.
- Entry is next 1H bar open.
- Features use only bars at or before signal time.
- No synthetic filling of missing candles.
- If stop and target are both touched inside the same OHLC bar, stop is assumed first.

## Risk baseline
- structural stop from recent swing ± 0.2 ATR
- max stop distance 1.5 ATR
- nearest visible obstacle must allow at least 2R
- exit baseline: stop, 2R target, or 4-bar time exit

## Cost-model correction
The first empirical run exposed a critical modeling error: applying a common bps-of-quoted-price fee/slippage proxy across futures with different quotation scales and contract multipliers is invalid.

Therefore R1.3.3 final metrics are gross of real transaction costs and explicitly carry:
`cost_model_status = N/A_CONTRACT_SPECIFIC_COSTS_PENDING`.

Real MOEX/exchange/broker fees, tick value and slippage must be modeled per contract before any strategy GO.

## RVOL
RVOL uses the median volume of the same clock hour over the previous 10 observations. Threshold = 1.0. This is a baseline hypothesis, not an optimized parameter.

## Empirical slice
Period: 2026-06-01 to 2026-08-31.

Contracts:
- MXU6 — IMOEX/MIX family
- SiU6 — USD/RUB family
- SRU6 — SBER ordinary shares
- GZU6 — GAZP
- LKU6 — LKOH

Observed 1H bars: approximately 1,205–1,315 per contract.

## Results
The strategy does not have enough accepted trades for statistical evaluation on this slice:
- MX: M0/M1/M5 = 1 trade
- Si: M0/M1/M5 = 2 trades
- SR: 0 trades
- GZ: M0=2, M1=2, M5=1
- LK: 0 trades

Any PF/expectancy shown for these tiny samples is descriptive only and must not be interpreted as evidence of edge.

## Signal-density funnel
Across the five contracts:
- Regime + Trigger candidates: 598
- Location generally preserves most candidates (80–92% by instrument)
- RVOL preserves roughly half to two-thirds
- STOP_INVALID_OR_TOO_WIDE: 368 candidates (~61.5%)
- INSUFFICIENT_RR: 221 candidates (~37.0%)
- only 6 non-overlap-agnostic candidates pass the baseline Risk Gate (~1%)

The dominant bottleneck is therefore the Risk Gate, not Location or RVOL.

This does NOT justify relaxing 1.5 ATR or 2R merely to create trades. Threshold sensitivity must be tested on a substantially longer roll-chain sample and evaluated for stable plateaus rather than optimized on this quarter.

## Gate decision
**R1.3.3 = RESEARCH NO-GO / IMPLEMENTATION PASS.**

PASS:
- public MOEX data acquisition
- bounded range collection
- point-in-time feature logic
- M0/M1/M5 ablation engine
- regression tests
- empirical replay
- diagnostic funnel

NO-GO:
- insufficient number of accepted trades
- single-contract-quarter sample is not representative
- contract-specific cost model not yet implemented
- no evidence yet that M0/M1/M5 has stable positive edge

## Next release
R1.3.4 should be **Historical Roll-Chain & Risk-Gate Sensitivity Validation**:
1. build deterministic quarterly futures roll chains over multiple years;
2. validate OHLCV continuity and roll rules;
3. add instrument-specific fee/tick/multiplier/slippage model;
4. rerun M0/M1/M5 across bull/bear/range/high-vol/low-vol periods;
5. test broad sensitivity for max stop ATR and minimum R/R without optimizing to a sharp best value;
6. use IS/OOS/walk-forward separation;
7. only then decide whether the Risk Gate is structurally too restrictive.
