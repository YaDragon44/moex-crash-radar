# VKCO Monitor R1.5 — Position Management

## Goal
Add simple stateful management of an accepted READY trade without adding broker integration, a database, or a new service.

## Position lifecycle
OPEN → TP1 → TRAILING → CLOSED_PROFIT / CLOSED_STOP.

`TP2` is emitted as a management event and switches the position into `TRAILING` mode.

## Rules
- a READY signal opens one logical LONG position in `state.json`;
- while a position is active, new entry signals are suppressed;
- TP1 moves stop to breakeven;
- TP2 moves stop to at least TP1 and activates trailing;
- trailing stop can only move upward;
- TP3 closes the position as `CLOSED_PROFIT`;
- stop hit closes the position as `CLOSED_STOP`;
- if stop and target are both inside one OHLC candle, stop is assumed first (conservative rule);
- no automatic broker orders are sent.

## Telegram
Notifications are sent only when the position status materially changes: TP1, TP2, trailing-stop update, CLOSED_PROFIT, CLOSED_STOP.

## Preserved from R1.4.2
- 1,000,000 RUB default trading capital;
- 0.5% default risk per trade;
- adaptive support/resistance;
- RVOL confirmation;
- IMOEX market filter;
- official VK IR event-risk gate;
- heartbeat/error alerts;
- anti-duplicate signal state;
- GitHub Actions + MOEX + Telegram architecture.

## Scope limitation
R1.5 manages a model position, not a broker-confirmed fill. Entry, partial exits and stop execution remain user actions. Broker synchronization is intentionally out of scope.

## Production gate
PR regression PASS → merge → main production workflow PASS.
