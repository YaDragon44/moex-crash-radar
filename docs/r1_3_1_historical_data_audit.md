# R1.3.1 — Historical Data Audit

Status: DATA GATE / BASELINE AUDIT

## Scope
Target research basket: IMOEX-family futures, Si, SBER, GAZP, LKOH. The objective is to determine which datasets can be used in a no-look-ahead 1H backtest of MOEX OI Flow v1.0.

## Verified public-source semantics
1. MOEX Analytical Products states that the intraday open-interest product provides statistics for liquid futures held by individuals and legal entities at five-minute intervals. Access requires subscription.
2. MOEX public contract pages show long/short positions for individuals/legal entities and explicitly state that the data is aggregated across expiries. They show daily change versus the previous trading day.
3. MOEX derivatives archive exposes daily contract-level trading results including Open Interest.
4. Public MOEX delayed market pages expose current contract-level Open Interest and confirm active liquid series such as MIX/MXI/IMOEXF, Si, SBRF, GAZR and LKOH families.
5. Public ISS concrete-contract candle endpoint is suitable for 1H OHLCV collection, but futures rollover/expiry must be explicit. No synthetic continuous series may be created without a documented roll rule.

## Critical conclusion
The public data currently verified is NOT sufficient to claim a full historical 1H backtest of Legal/Retail intraday positioning.

Daily participant positioning must be treated as DELAYED CONTEXT only. It must never be injected into earlier 1H bars from the same trading day. Historical intraday OI/participant data remains N/A until an export/subscription dataset is supplied with verified event_time and available_time.

## Coverage matrix

| Dataset | Public status | Backtest role | Quality |
|---|---|---|---|
| 1H OHLCV, concrete FORTS contract | available via ISS | M0/M1/M5 | READY |
| Daily contract OI | derivatives archive/current pages | daily context / validation | READY |
| Intraday OI history | advertised 5m product; historical export not yet verified | M2 | N/A |
| Daily Legal/Retail | public aggregate across expiries, daily change | delayed state only | DELAYED |
| Intraday Legal/Retail history | advertised product but historical export/access not verified | M3/M4/FULL | N/A |

Public-baseline weighted Quality Coverage = 52.0% under the R1.3.1 audit weights. This number is a data-coverage indicator, not a confidence/probability score.

## Instrument audit

### IMOEX family
Current liquid families verified publicly include MIX-9.26, MXI-9.26 and perpetual IMOEXF. Use one defined signal family in a test; do not mix contract scales. For expiry contracts, roll must be deterministic and documented.

### Si
Current public delayed data confirms liquid Si-9.26 and Si-12.26 with substantial contract OI. Suitable for OHLCV baseline; participant intraday historical coverage remains N/A.

### SBER
Current public delayed data confirms SBRF-9.26 and SBRF-12.26 as active ordinary-share futures. SBPR is a separate preferred-share family and must not be mixed into SBRF history.

### GAZP
Current public delayed data confirms GAZR-9.26 as an active liquid family. Suitable for price/volume baseline subject to roll audit.

### LKOH
Current public delayed data confirms LKOH-9.26 and later expiries. Liquidity varies sharply by expiry; front/next roll rule is mandatory.

## No-look-ahead contract
Every historical record must have two timestamps:
- event_time — when the market event belongs;
- available_time — when the algorithm could actually know it.

A feature at decision time T may use only records where available_time <= T.

For 1H candles, the candle is usable only after close. For daily participant positioning, the value is usable only from the next eligible decision after its publication. Historical rows without reliable available_time are N/A.

## Allowed ablation after R1.3.1
With public data alone:
- M0 Price Structure: GO
- M1 + Location: GO
- M2 + Intraday OI: NO-GO / N/A pending historical intraday dataset
- M3 + Legal: NO-GO / N/A for hourly signal
- M4 + Retail: NO-GO / N/A for hourly signal
- M5 + RVOL: GO
- FULL: NO-GO / N/A

Daily participant positioning may be tested later as a separate delayed context overlay, but must not be presented as M3/M4 hourly positioning until historical intraday availability is proven.

## Required next gate
R1.3.2 should build the honest public-data baseline M0/M1/M5 with deterministic futures roll handling and commission/slippage assumptions. In parallel, obtain/verify subscribed historical 5-minute OI + participant exports. Only after that dataset passes timestamp/coverage QA should M2-M4 and FULL be enabled.
