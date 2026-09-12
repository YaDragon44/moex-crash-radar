# VKCO Monitor R1.2 — Signal Quality

## Goal
Improve signal quality without adding infrastructure or a large indicator stack.

## Architecture
GitHub Actions → MOEX ISS → VKCO adaptive trigger → IMOEX market filter → Telegram.

## Changes
- removed stale fixed trigger levels 127–130 / 141;
- added adaptive support/resistance from the previous 20 completed 10m candles;
- breakout requires two closes above adaptive resistance;
- breakout candle requires RVOL >= 1.20;
- spring requires sweep/reclaim of adaptive support and next-candle hold;
- spring candle requires RVOL >= 1.30;
- long READY requires IMOEX market filter PASS;
- IMOEX filter: latest close not below 20-bar average by >0.5% and 1h return >= -0.70%;
- stop and TP1/TP2/TP3 are derived from current structure/risk instead of old absolute prices;
- Telegram message includes adaptive levels, RVOL and IMOEX context.

## Explicitly not added
- no RSI/MACD/ADX/Bollinger stack;
- no database;
- no VPS/Cloudflare;
- no broker integration;
- no auto-trading;
- no news NLP layer.

## Gate
1. Regression tests PASS.
2. Real MOEX VKCO candles PASS.
3. Real IMOEX candles PASS when a raw signal exists.
4. No Telegram READY when volume filter fails.
5. No Telegram READY when market filter fails.
6. Main production workflow PASS after merge.

## Known limitation
GitHub scheduled runs are best-effort and may be delayed. R1.1 heartbeat remains the operational control.
