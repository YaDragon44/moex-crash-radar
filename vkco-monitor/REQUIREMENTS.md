# VKCO Monitor — Requirements v2.0

**Status:** CANONICAL BASELINE  
**Scope:** VKCO model/paper trade monitoring on MOEX.  
**Principle:** real data -> explicit gates -> risk plan -> model lifecycle -> evidence.

## 1. Data
- Use real MOEX ISS data for VKCO/TQBR.
- Primary trigger timeframe: completed M10 candles.
- Never fabricate or silently substitute market data.
- Stale, incomplete or invalid critical data must fail closed.
- Production scheduling may be delayed by GitHub Actions and is not HFT.

## 2. Signal
Only two production LONG setups are authorized:
1. Adaptive Spring.
2. Adaptive Breakout + Hold.

Adaptive support/resistance use the previous 20 completed candles excluding the last 3 trigger candles.

Confirmation:
- Breakout RVOL >= 1.20.
- Spring RVOL >= 1.30.
- IMOEX market filter must pass.
- Official VK IR Event Risk Lite must not block READY.

If any mandatory gate fails, status is WAIT. Strategy parameters are frozen during Production Observation.

## 3. Risk
For every READY trade plan:
- production risk setting remains 0.5% of configured trading capital;
- Entry, Stop, TP1, TP2 and TP3 must be explicit;
- stop must invalidate the trade hypothesis;
- sizing must respect both monetary risk budget and available capital/notional;
- quantity must be rounded down to the current official MOEX LOTSIZE;
- missing/invalid critical sizing metadata must fail closed;
- no leverage is assumed unless explicitly introduced by a future authorized requirement.

## 4. Model position lifecycle
The system manages a MODEL/PAPER position, not a broker-confirmed fill.

Lifecycle:
WAIT -> READY -> OPEN -> TP1 -> TP2/TRAILING -> CLOSED.

Rules:
- suppress new entries while a model position is active;
- TP1 moves stop to breakeven;
- TP2 activates trailing and stop cannot move down;
- TP3 closes profit;
- stop closes the model position;
- ambiguous same-candle stop/target execution is handled conservatively;
- completed model trades are journaled idempotently.

## 5. Evidence
Journal metrics include at least:
- trade count;
- Win Rate;
- Average R;
- Profit Factor;
- Expectancy R.

Observation gate:
- 10 closed model trades: diagnostic review only;
- prefer 20 closed model trades before strategy tuning.

No threshold/strategy optimization is authorized before sufficient evidence.

## 6. Delivery
- Telegram: material READY/lifecycle/error/heartbeat notifications.
- Public dashboard: read-only.
- Dashboard and chart use sanitized VKCO Live State.
- Live State must expose actual completed M10 candles; dashboard must show degraded/unavailable state rather than invent data.
- Secrets must never enter public state, source documentation or logs.

## 7. Scope lock
Intentionally out of scope during Production Observation:
- broker API and automatic orders;
- VPS, database, Redis, Docker, Cloudflare or new backend services;
- ML/AI signal generation;
- additional trading setups;
- Elliott/Fibonacci or additional dashboard indicators used as trading gates;
- strategy tuning without evidence.

Runtime, data-integrity, state-transition and risk-safety defects may be hotfixed without violating the strategy freeze.

## 8. Acceptance
A release is not production-ready merely because source code exists.
Required where applicable:
1. targeted regression PASS;
2. repository CI/release gate PASS;
3. production workflow PASS;
4. for UI changes, public Pages deployment and public dashboard/data gate PASS;
5. canonical documentation/checkpoint updated after an accepted material release.
