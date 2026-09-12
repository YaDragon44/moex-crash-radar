# VKCO Monitor R1.4.2 — Capital Configuration

## Goal
Enable concrete position sizing in READY Telegram messages using the accepted VKCO trading capital while keeping the R1.4.1 risk policy unchanged.

## Configuration
- Trading capital: 1,000,000 RUB by default.
- Risk per trade: 0.5% by default.
- Maximum planned risk per trade at default settings: 5,000 RUB.
- `TRADING_CAPITAL_RUB` GitHub Variable may override the default later.
- `RISK_PCT` GitHub Variable may override the default later.

## Preserved
- adaptive support/resistance;
- RVOL confirmation;
- IMOEX filter;
- official VK IR event-risk gate;
- heartbeat/error alerts;
- anti-duplicate state;
- Telegram delivery;
- no broker integration and no auto-trading.

## Position sizing
Allowed risk = capital × risk %.

Shares = floor(allowed risk / (Entry - Stop)), rounded down to lot size.

The stop remains structural. Position size adapts to the stop distance; the stop is not widened to fit a desired position.

## Production gate
PR regression PASS → merge → main production workflow PASS.
