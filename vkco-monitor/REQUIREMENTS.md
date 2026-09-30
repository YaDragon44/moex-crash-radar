# VKCO REQUIREMENTS — CURRENT BASELINE

**As of:** 2026-09-30

## Scope
Only VK / VKCO. Preserve capital, evidence integrity and simplicity.

## Functional
1. Fetch real VKCO MOEX candles and fail closed on stale/missing critical data.
2. Run four independent strategies: S1 production/frozen; S2/S3/S4 SHADOW.
3. S1 authorized setups only: Adaptive Wyckoff Spring and Adaptive Breakout + Hold.
4. Mandatory S1 IMOEX and official VK IR event-risk gates.
5. Risk per S1 model trade: 0.5%; no broker execution.
6. Persist model lifecycle, journal and deduplicated decision evidence.
7. S4 uses completed H1 candles, H1 local/structural S/R, H1 IMOEX/event-risk and read-only MA50/MA200 context.
8. Dashboard must distinguish market facts, strategy decisions, fundamentals, valuation and model positions.
9. Official VK IR fundamentals must fail closed when required source fields cannot be verified.
10. New LONG lifecycle state requires `stop < entry < TP1 < TP2 < TP3`.

## Non-functional
- No invented data.
- No weakening gates to achieve PASS.
- Strategy #1 freeze until evidence threshold.
- Independent strategy state/journals.
- Secrets never published.
- Static/GitHub Actions architecture unless a new requirement proves a backend is necessary.
- Production claims require fresh evidence.

## Observation gates
- 10 S1 closed model trades: diagnostic review only.
- Prefer >=20 S1 closed model trades before tuning.
- S4 stays SHADOW until adequate sample and explicit review.
