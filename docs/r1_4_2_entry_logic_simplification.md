# R1.4.2 — Entry Logic Simplification

## Why
R1.4.1 public validation showed that making RVOL and RSI universal hard gates did not improve the aggregate 4-hour forward signal and the combined RVOL+RSI gate degraded it. R1.4.2 therefore simplifies the operational radar.

## Hard gates
1. Technical data quality is available.
2. 1H trend is directional: EMA20 > EMA50, EMA20 slope up and price > EMA20 for LONG; symmetric for SHORT.
3. Confirmed 1H price trigger: close above previous 1H high for LONG; below previous 1H low for SHORT.

## Soft confirmations
- RVOL >= 1.20
- RSI momentum confirmation: LONG 55–65 rising; SHORT 35–45 falling
- OI delta >= +0.50%, when point-in-time data is available
- Legal/Retail divergence, when authenticated intraday FUTOI is available

Missing OI/FUTOI remains N/A and never becomes neutral or green.

## States
- AVOID — no valid directional trend / hard trend gate fails.
- WAIT — trend valid, trigger not confirmed.
- ENTRY LONG / ENTRY SHORT — hard gates pass.
- CONFIRMED LONG / CONFIRMED SHORT — ENTRY plus at least two available positive confirmations.
- LATE LONG / LATE SHORT — hard gates pass but RSI indicates overextension (LONG >68, SHORT <32); do not chase.

## Important interpretation
CONFIRMED is not a statistical probability of profit. RSI/RVOL/OI/positioning are confidence layers, not independent voting proof. The design must remain market-specific after further validation.
