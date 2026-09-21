# R1.5.3-A — Public Historical Feasibility and Preregistration

**Status:** PREREGISTERED / FEATURE DEFINITIONS LOCKED / EMPIRICAL VALIDATION NOT RUN  
**Owner:** `YaDragon44/moex-crash-radar`  
**Production:** NO-GO

## Feasibility result

**Technical feasibility: PASS.** Existing source code already provides public MOEX ISS daily candles for IMOEX and shares, historical pagination, breadth, volume-distribution, volatility calculations, and point-in-time replay. The repository contains the official MOEX constituent archive for 2019–2026. No new collector, data store or analytics owner is required.

**Empirical conclusion: not yet calculated.** This document does not claim lead time, precision, recall or incremental value. Those require the locked replay below.

## Locked source and time semantics

| Item | Locked rule |
|---|---|
| Price, volume, volatility | MOEX ISS daily candles: IMOEX and active share universe |
| Breadth denominator | `data/imoex_constituents_2019_2026.json`, sourced from the official MOEX index-base archive |
| Historical period | 2019-03-22 through 2026-09-18; later data is excluded from the first run |
| Event time | the trade date of the daily candle |
| Available / decision time | next trading session at 10:00 Europe/Moscow; this conservative convention avoids using a same-session final candle |
| Minimum equity coverage | 70% of the effective historical constituent basket, with no forward-fill |
| Missing data | `INSUFFICIENT_DATA`; it cannot satisfy a condition |

## Locked outcome and horizon

A warning outcome occurs on day *t* when the minimum IMOEX close in the next **20 trading sessions** is at least **8% below** the close at *t*. This is an evaluation label only, not a forecast or production threshold.

The historical rows are split before review:

- development: 2019-03-22–2023-12-29;
- final holdout: 2024-01-01–2026-09-18.

No label, horizon or split may be changed after seeing results.

## Deterministic feature definitions for R1.5.3-B

All comparisons use the existing point-in-time `DailyEvidence` fields for day *t*; no new collector, model, score or recalibration is introduced. A missing score, coverage below 70%, or `INSUFFICIENT_DATA` makes the relevant condition unavailable and cannot satisfy `DISTRIBUTION_WATCH`.

| Condition | Locked definition |
|---|---|
| `PRICE_RESILIENT` | `market_structure_score < 50` **and** the prior five-session IMOEX return is greater than `-3%`. |
| `BREADTH_DETERIORATING` | `breadth_score >= 40`. |
| `VOLUME_WEAKENING` | `volume_distribution_score >= 40`. |
| `VOLATILITY_RISING` | `volatility_liquidity_score >= 50`. |
| `DISTRIBUTION_WATCH` | `PRICE_RESILIENT AND BREADTH_DETERIORATING AND (VOLUME_WEAKENING OR VOLATILITY_RISING)`. |

The source formulas and historical windows are those already committed before this lock. Their thresholds, the 70% coverage gate, outcome, horizon, development/holdout split and M0–M4 comparison are frozen for the first replay. No metric review may alter them. Any needed future variant is a separate preregistered experiment and cannot overwrite this result.

## Locked candidate comparisons

- M0: Price only;
- M1: Price + Breadth;
- M2: Price + Breadth + Volume;
- M3: Price + Breadth + Volatility;
- M4: Price + Breadth + Volume + Volatility.

A candidate observation is usable only after M4 is compared with M0 on the untouched holdout. Required reporting: number of rows, coverage, missing periods, lead time, false-alarm rate, precision, recall, persistence, incremental contribution and failure cases.

## Permitted state during validation

`DISTRIBUTION_WATCH` is research analysis only. It may be observed only under the R1.5.3 foundation rule and must remain `NOT_OBSERVED` or `INSUFFICIENT_DATA` otherwise. It never changes Crash Score, EXIT Gate, Crash State, RADAR actions or the public RADAR UI.

## Next gate

Run the locked historical replay and publish a reproducible evidence report with exactly one result: **PASS**, **FAIL** or **INCONCLUSIVE**. Only PASS with material incremental value may request a separate owner decision for source projection.
