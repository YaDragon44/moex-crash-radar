# R1.3.2 — FUTOI Coverage & 1H Alignment Gate

Status: DATA QUALITY GATE

## Goal
Validate whether historical MOEX FUTOI can be aligned to 1H trading decisions for MX / SI / SR / GZ / LK without look-ahead and with sufficient coverage for M2–M4/FULL ablation.

## Official source semantics
MOEX documents FUTOI as intraday futures open-interest statistics split between individuals (FIZ) and legal entities (YUR). MOMENT is the time of the latest trade included in the statistic; SYSTIME is the publication timestamp. Data retrieval is available through ISS, but viewing/downloading requires an active subscription/authenticated session.

Therefore:
- MOMENT = event_time;
- max(FIZ.SYSTIME, YUR.SYSTIME) = available_time for a complete pair;
- an hourly decision at T may use only a complete FIZ+YUR pair whose available_time <= T;
- daily public positioning must never substitute for FUTOI in M3/M4.

## Alignment algorithm
1. Parse FUTOI rows.
2. Pair FIZ/YUR by ticker + MOMENT.
3. For each closed 1H decision timestamp, select the latest complete pair published no later than the decision.
4. Compute Total OI from gross long side across FIZ+YUR, not by summing their offsetting net positions.
5. Compute ΔOI, ΔRetailNet and ΔLegalNet only across already aligned point-in-time-safe snapshots.
6. No future SYSTIME may be forward-filled into an earlier 1H bar.

## Gate thresholds — baseline hypotheses
- Alignment coverage >= 95% of requested 1H decision hours.
- Median publication lag (SYSTIME - MOMENT) <= 300 sec.
- Zero look-ahead violations.
- Complete FIZ/YUR pair required.

Thresholds are validation gates, not optimized strategy parameters.

## Current factual status
The implementation and regression tests are READY, but the real instrument coverage run is BLOCKED_AUTH in the current environment because MOEX FUTOI requires subscription/authenticated access.

This is a correct NO-GO for the data gate, not a product failure.

Current expected matrix until authenticated FUTOI is supplied:

| Ticker | Market family | Coverage run | 1H alignment | M2/M3/M4/FULL |
|---|---|---:|---:|---:|
| MX | IMOEX | BLOCKED_AUTH | N/A | NO-GO |
| SI | USD/RUB | BLOCKED_AUTH | N/A | NO-GO |
| SR | SBER | BLOCKED_AUTH | N/A | NO-GO |
| GZ | GAZP | BLOCKED_AUTH | N/A | NO-GO |
| LK | LKOH | BLOCKED_AUTH | N/A | NO-GO |

M0/M1/M5 remain independently testable from public price/volume data.

## Acceptance criteria after credentials/data are available
For each ticker report:
- requested start/end;
- raw rows;
- complete FIZ/YUR pairs;
- unique trading days;
- first/last MOMENT;
- point-in-time violations;
- 1H decision hours;
- aligned hours;
- alignment coverage %;
- missing-hour %;
- median/max publication lag;
- READY / FAIL / N/A.

FULL becomes READY only when every instrument selected for the pooled test passes its own data gate. A ticker may be excluded from the research universe only by an explicit documented decision, never merely to improve results.

## Next step
After authenticated FUTOI becomes available, run:

`python scripts/run_r1_3_2_coverage_alignment.py --tickers MX,SI,SR,GZ,LK --start YYYY-MM-DD --end YYYY-MM-DD`

Then intersect safe FUTOI decision timestamps with actual closed 1H futures-contract bars under the deterministic roll policy and proceed to M0→FULL ablation only for READY instruments.
