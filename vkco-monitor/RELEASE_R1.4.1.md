# VKCO Monitor R1.4.1 — Risk Configuration

## Goal
Make the trade-plan layer safer and simpler to operate without hardcoding a personal capital amount.

## Decision
- Default risk per trade: 0.5% if `RISK_PCT` is absent.
- Trading capital remains external via `TRADING_CAPITAL_RUB`.
- No position sizing is produced when capital is absent.
- No broker integration and no auto-trading.

## Production gate
1. Regression tests PASS.
2. Pull request merged to `main`.
3. Production workflow PASS.

## Rationale
A conservative default risk percentage is operationally safe, while guessing or hardcoding capital is not. Capital must remain an explicit user-controlled input.
