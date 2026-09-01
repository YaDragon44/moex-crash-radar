# R1.4.0 BTC Entry Radar MVP

Status: CANDIDATE / decision-support only.

## Purpose
Turn the validated research findings into a usable BTC spot entry decision layer without claiming calibrated prediction.

## State machine
NO TRADE -> WATCH -> ARMED -> LONG READY -> MANAGE.

## Required inputs
- Fear & Greed (Crowd context)
- BTC 4H structure / 3-bar breakout confirmation
- BTC Open Interest regime as risk context, not mandatory entry alpha
- ATR14 + local swing low for risk gate
- Quality Gate

## Rules
1. STALE/N/A or missing required input -> NO TRADE.
2. Stop distance >2 ATR -> NO TRADE.
3. OI OVERHEATED -> NO TRADE / DO NOT CHASE.
4. F&G >60 -> NO TRADE / DO NOT CHASE in MVP.
5. F&G <=35 + BTC still making local low -> WATCH.
6. F&G <=35 + no new local low + no 4H confirmation -> ARMED.
7. F&G <=35 + no new local low + 4H confirmation -> LONG READY.
8. Position open -> MANAGE.

## Size modifier
- 100% standard size: F&G <=25 + OI DELEVERAGING + price confirmed.
- 75%: normal validated fear setup.
- 50%: OI MODERATE_BUILD.
- 0%: NO TRADE.

`standard size` is a multiplier of the user's risk-budgeted position, not percent of portfolio capital. Initial risk budget remains 0.5% of trading capital per trade until separately validated.

## Non-goals
RSI, EMA, Funding and Long/Short positioning are not required for R1.4.0. They must earn inclusion through incremental OOS validation.

## Quality / interpretation
Crowd and risk scores are not statistical probabilities. OI is used as leverage/risk context. LONG READY means the MVP conditions permit a selective long; it is not a guarantee or automatic order.
