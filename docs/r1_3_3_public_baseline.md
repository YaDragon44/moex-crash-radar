# R1.3.3 — Public Baseline Backtest M0/M1/M5

Status: DEVELOPMENT / PUBLIC-DATA BASELINE

## Objective
Measure the standalone edge of the public-data core before FUTOI is enabled.

Ablation:
- M0 = Price Structure / regime + closed-bar trigger
- M1 = M0 + Location
- M5 = M1 + same-hour RVOL

OI, Legal and Retail positioning are deliberately excluded. Their incremental value must be measured later against this baseline.

## Point-in-time rules
- Only closed 1H bars may create a signal.
- Entry is next 1H bar open.
- Features use only bars at or before signal time.
- No synthetic filling of missing candles.
- If stop and target are both touched inside the same OHLC bar, stop is assumed first (conservative ambiguity rule).

## Risk / cost baseline
- structural stop from recent swing ± 0.2 ATR
- max stop distance 1.5 ATR
- nearest visible obstacle must allow at least 2R
- exit baseline: stop, 2R target, or 4-bar time exit
- baseline round-trip fee: 2 bps
- baseline round-trip slippage: 2 bps

Costs are deducted in R-units per trade.

## RVOL
RVOL uses the median volume of the same clock hour over the previous 10 observations. Current threshold is 1.0. This is a baseline hypothesis, not an optimized parameter.

## Current research universe
First public replay uses the September 2026 liquid contracts:
- MXU6 — IMOEX/MIX family
- SiU6 — USD/RUB family
- SRU6 — SBER ordinary shares
- GZU6 — GAZP
- LKU6 — LKOH

These exact contract codes are used only for the initial public baseline slice. A multi-year study requires deterministic contract-roll construction and is a separate gate.

## Acceptance logic
R1.3.3 is not allowed to claim strategy viability merely because code runs.

For each model and instrument report:
- trades
- win rate
- expectancy R
- profit factor
- max drawdown R
- total net R

A model with too few trades is PARTIAL / insufficient evidence.

Research target for later OOS validation remains approximately:
- Profit Factor > 1.3
- Expectancy > 0.15R/trade
- survives costs/slippage
- stable across more than one instrument

These are evaluation targets, not optimized entry thresholds.

## Critical limitation
A single active-contract replay cannot establish long-run robustness. It is used to verify the public-data engine and produce the first empirical baseline. R1.3.4 should add deterministic historical roll chains and longer IS/OOS/walk-forward samples before any GO on strategy edge.
