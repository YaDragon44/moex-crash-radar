# MOEX OI Flow 1H — Trading Algorithm v1.0

Status: BASELINE FOR BACKTEST
Release: R1.3
Issue: #3

## Objective
Test whether Open Interest and legal/retail positioning add incremental out-of-sample value to a 1H MOEX futures strategy after controlling for 4H regime, 1H location and price structure.

## Decision chain
DATA QUALITY → 4H REGIME → 1H LOCATION → OI → POSITIONING → RVOL → 1H TRIGGER → RISK → ENTRY/EXIT.

Outputs: LONG, SHORT, WAIT, NO TRADE. No composite probability is produced.

## Timing / no-look-ahead contract
1. Every feature must carry `event_time` and `available_time`.
2. A feature may affect a decision only when `available_time <= decision_time`.
3. Entry is always the next 1H bar open after a fully closed trigger bar.
4. Missing positioning/OI is never forward-filled across an unknown publication boundary.
5. End-of-day participant-position data must not be treated as intraday information. If only daily positioning is available, it becomes a session/state filter available only after its official publication time.
6. Intraday 5-minute OI/participant data may be used only for periods and instruments for which the subscribed dataset is actually available historically.
7. Contract roll and aggregation across expiries must be explicit; no silent stitching.

## Data audit — mandatory before historical claims
For each instrument and field report:
- source and endpoint/file
- granularity
- event timestamp
- publication/availability timestamp
- timezone
- coverage start/end
- missing rate
- duplicate rate
- stale intervals
- contract/underlying mapping
- roll rule
- whether the field is contract-specific or aggregated across expiries
- LIVE / DELAYED / STALE / N/A status

Required fields:
- 1H OHLCV
- 4H OHLCV derived only from closed 1H bars
- Open Interest
- legal long / legal short
- retail long / retail short
- trading calendar / session boundaries
- contract metadata and expiry

## Important source constraint
MOEX public futures cards expose individual/legal long/short positions and daily change, typically aggregated across expiries of the same underlying. MOEX also describes a separate intraday Open Interest analytical product with five-minute updates that requires subscription. Therefore daily participant-position snapshots are not assumed to be known every hour.

## Baseline gates
- 4H BULL: confirmed HH + HL; BEAR: LH + LL; RANGE/UNKNOWN = NO TRADE.
- Valid location: PDH/PDL or confirmed 1H/4H structural level; mid-range = NO TRADE.
- OI expansion required; absolute ΔOI percentile baseline >= 75.
- Positioning is used as delta/transition evidence, never as `legal = smart money` truth.
- RVOL baseline >= 1.0; breakout >= 1.2.
- Trigger: pullback + HL/LH break, or breakout + retest. No entry on breakout candle.
- Stop: structural swing ± 0.2 ATR(14); reject if stop distance > 1.5 ATR.
- Nearest structural target must offer >= 2R.
- Reject if next-open entry is > 0.5 ATR from trigger reference.
- Risk baseline 0.5% equity.

## Exit baseline
- 33% at +1R.
- Move stop to breakeven only after a closed 1H bar confirms beyond +1R.
- 33% at +2R.
- Remaining 34% trails confirmed 1H swing structure.
- Time exit after 4 closed bars if MFE has not reached +0.5R.

## Ablation
M0 Price Structure
M1 + Location
M2 + OI
M3 + Legal positioning
M4 + Retail positioning
M5 + RVOL
FULL + all risk/location gates

## Validation
Chronological in-sample / out-of-sample plus walk-forward. No random split. Compare per instrument and pooled. Include commissions/slippage and contract roll costs where applicable.

Primary metrics: expectancy in R, profit factor, max drawdown, Sharpe/Sortino, median R, trades/year, MAE/MFE, consecutive losses, NO TRADE distribution, regime stability, instrument stability, cost sensitivity.

Preliminary research GO gate: OOS PF > 1.3, expectancy > 0.15R/trade, acceptable drawdown, not dependent on one instrument, survives costs, and OI/positioning variants demonstrate incremental value versus M0/M1. These are gates, not optimization targets.
