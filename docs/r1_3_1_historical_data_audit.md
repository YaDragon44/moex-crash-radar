# R1.3.1 — Historical Data Audit

Status: DATA GATE / BASELINE AUDIT

## Scope
Target research basket: IMOEX-family futures, Si, SBER, GAZP, LKOH. The objective is to determine which datasets can be used in a no-look-ahead 1H backtest of MOEX OI Flow v1.0.

## Verified MOEX semantics
1. MOEX Analytical Products states that FUTOI/open-interest statistics for liquid futures held by individuals and legal entities are updated at five-minute intervals.
2. MOEX announced that AlgoPack products other than MegaAlerts have historical data from 2020. FUTOI is explicitly listed as open positions of individuals/legal entities.
3. FUTOI visual pages show intraday timestamps and separate FIZ/YUR long/short positions, open interest and directed/net positioning by underlying family.
4. AlgoPack/FUTOI access is subscription/API-key based. Documentation-level historical capability does not by itself prove complete per-instrument coverage for our test window.
5. MOEX public contract pages show daily long/short data aggregated across expiries; these daily figures must not be injected into earlier 1H bars.
6. MOEX derivatives archive exposes daily contract-level Open Interest.
7. Public ISS concrete-contract candle endpoint is suitable for 1H OHLCV collection, but futures rollover/expiry must be explicit.

## Critical conclusion
The earlier assumption that historical intraday Legal/Retail positioning was unavailable is corrected.

MOEX confirms that FUTOI provides intraday 5-minute FIZ/YUR positioning and historical data from 2020. Therefore M2/M3/M4/FULL are technically feasible. However, they remain disabled in the executable backtest until an actual FUTOI export is obtained and passes per-instrument coverage, pairing and timestamp QA.

This distinction is deliberate:
- capability documented by MOEX = PARTIAL;
- dataset actually fetched, timestamped and coverage-tested = READY.

## Coverage matrix

| Dataset | Verified status | Backtest role | Quality |
|---|---|---|---|
| 1H OHLCV, concrete FORTS contract | public ISS | M0/M1/M5 | READY |
| Daily contract OI | derivatives archive/current pages | validation/context | READY |
| Intraday OI history | FUTOI, 5m, history from 2020; subscription required | M2 | PARTIAL until export audit |
| Daily Legal/Retail | public aggregate across expiries | delayed context only | DELAYED |
| Intraday Legal/Retail history | FUTOI FIZ/YUR, 5m, history from 2020; subscription required | M3/M4/FULL | PARTIAL until export audit |

Documentation-level weighted Quality Coverage = 76.0% under R1.3.1 weights. This is a data-readiness indicator, not model confidence or probability.

## Instrument audit

### IMOEX family
Current liquid families verified publicly include MIX/MXI and perpetual IMOEXF. FUTOI exposes MX (IMOEX) positioning. The backtest must use one defined price series/family and document any mapping between price contract and aggregate underlying-family FUTOI.

### Si
Current public delayed market data confirms liquid Si expiries. FUTOI exposes Si/USDRUB positioning intraday. This is a prime candidate for the first full FUTOI coverage run.

### SBER
Current market data confirms SBRF ordinary-share futures; SBPR is a separate preferred-share family and must not be mixed. FUTOI exposes SR (Sber ordinary share) positioning.

### GAZP
Current market data confirms GAZR futures. FUTOI exposes GZ (Gazprom) positioning.

### LKOH
Current market data confirms LKOH futures and later expiries. Price history is suitable subject to explicit roll rules. FUTOI per-underlying availability must be confirmed in the subscribed export before M3/M4 are enabled for LKOH.

## No-look-ahead contract
Every historical record must have two timestamps:
- event_time — when the market event belongs;
- available_time — when the algorithm could actually know it.

At decision time T the feature builder may use only records where available_time <= T.

For 1H candles, the candle is usable only after close. For FUTOI, the export's publication/system timestamp must be preserved; a market-moment timestamp alone is insufficient if publication delay exists. Daily public positioning is usable only from the next eligible decision after publication and is not a substitute for FUTOI.

## R1.3.1 Gate result
- M0 Price Structure: GO
- M1 + Location: GO
- M2 + Intraday OI: CONDITIONAL GO — historical capability confirmed; export QA required
- M3 + Legal: CONDITIONAL GO — FUTOI history confirmed; export QA required
- M4 + Retail: CONDITIONAL GO — FUTOI history confirmed; export QA required
- M5 + RVOL: GO
- FULL: CONDITIONAL GO — blocked until actual FUTOI coverage/timestamp audit passes

## Required next gate
R1.3.2 should perform two tracks:
1. Build and test the public-data baseline M0/M1/M5 with deterministic futures roll handling and commission/slippage assumptions.
2. Add the subscribed FUTOI loader/auditor and run a real coverage matrix for MX, Si, SR, GZ and LKOH-family availability: first/last timestamp, trading days, missing 5-minute snapshots, FIZ/YUR pairing, duplicate moments, publication lag and alignment to closed 1H bars.

Only after Track 2 passes may M2-M4/FULL be labelled DATA READY and enter OOS/walk-forward testing.
