# R1.4.3.1 — Historical Stop Gate

Status: IN TEST

Goal: empirically compare four simple stop candidates for existing R1.4.2 Trend + Trigger entries without changing entry semantics.

Candidates:
- SIGNAL_CANDLE
- ATR_1_0 (Wilder ATR14)
- ATR_1_5 (Wilder ATR14)
- SWING_3

Primary path horizon: 8 hourly bars. Metrics: stop-hit rate, risk distance, signed 8H exit result, MFE/MAE, instrument coverage.

Current public-data validation is a first gate, not final production calibration. Contract roll-chain, fees/slippage and broader chronology remain required before declaring a stop statistically validated.
