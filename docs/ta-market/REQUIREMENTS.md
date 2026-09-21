# TA Market Monitor — Requirements Baseline

## Goal
Answer one operational question safely: is there a sufficiently supported trade now? If yes, expose READY with a complete plan; otherwise WAIT. Never manufacture data or weaken safety to create a signal.

## Instruments and timeframes
- SBERP, VKCO, OZPH.
- D1, H1, M10 in production.
- Market context: IMOEX, TQBR breadth, CNYRUB_TOM, nearest active Brent futures contract.

## Signal contract
For a directional setup calculate Entry, Trigger condition, Stop/invalidation, TP1/TP2/TP3, R/R, Confluence Score and reason.
READY requires all applicable production gates: closed fresh candle, directional structure, price trigger, momentum confirmation, RVOL > 1.1x, at least two market-derived targets, R/R >= 2, and no simultaneous IMOEX+breadth veto against the direction.
Structural invalidation -> INVALID. Otherwise -> WAIT.

## Data safety
- Fail closed on missing/invalid critical data.
- Snapshot freshness safety gate <=25 minutes for READY in the live UI.
- Do not fabricate Event Risk when no reliable calendar exists.
- Market-context failures must be explicit.
- Persist source timestamps.

## Risk
Position sizing uses capital, risk %, MOEX lot size, commission and slippage. Stop belongs where the hypothesis is invalidated. No leverage is assumed by default.

## Observation
Persist state transitions, alert only new READY transitions, evaluate subsequent READY outcomes, and prevent model tuning on insufficient samples:
- <10 closed: INSUFFICIENT
- 10-29: PRELIMINARY
- >=30: USABLE

## Non-goals / backlog
No requirement to add FUTOI, CVD, Smart Money, Put/Call, full Wyckoff engine, or full Elliott engine before evidence justifies expansion.
