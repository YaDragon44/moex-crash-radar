# VKCO PROJECT CHECKPOINT

**Checkpoint date:** 2026-09-29 (Europe/Moscow)
**Project:** VKCO Trade Monitor + Control Room
**Repository:** YaDragon44/moex-crash-radar
**Status:** PRODUCTION OBSERVATION / STRATEGY #1 FREEZE

## Recovery anchor
Always inspect fresh `main` before acting. Production engine remains **R1.8**. No broker orders.

## Production paths
- Dashboard: `web/vkco-dashboard/index.html`
- Monitor: `vkco-monitor/monitor.py`
- Runtime: `vkco-monitor/run_r18.py`
- Exporter: `vkco-monitor/export_status.py`
- Strategy #4: `vkco-monitor/strategy4_h1.py`
- Workflow: `.github/workflows/vkco-monitor.yml`
- Observation gate: issue #61

## Current architecture
`GitHub Actions -> MOEX ISS -> strategy engines -> risk/evidence gates -> model lifecycle/journals -> sanitized status -> GitHub Pages`

No broker API/orders, VPS, DB, Redis, Docker, Cloudflare or ML.

## Strategies
### Strategy #1 — production / frozen
Adaptive Wyckoff Spring + Adaptive Breakout/Hold on completed M10. 20-candle adaptive levels; RVOL breakout >=1.20, spring >=1.30; IMOEX + official VK IR event-risk mandatory; risk 0.5%. Issue #61: 10 closed trades diagnostic only; prefer 20 before tuning.

### Strategy #2 — SHADOW
Independent M10 EMA50/EMA200 crossover benchmark. Separate state/journal. Does not affect S1.

### Strategy #3 — SHADOW
Independent M10 RSI14 + valuation/fair-value + EMA200 regime. Separate state/journal. Does not affect S1/S2.

### Strategy #4 — SHADOW / H1
S1-derived research strategy on completed H1 candles. Independent state/journal. H1 local S/R, repeated-pivot structural S/R zones, IMOEX H1 gate, official VK IR event-risk, model lifecycle and statistics. H1 MA50/MA200 trend context is read-only. H1 Decision Audit persists future WAIT/READY/BLOCKED evidence independently and does not alter signals.

## Dashboard
Current Control Room exposes four independent strategies, TradingView H1, RSI14, H1 MA50/MA200 trend context, H1 local/structural S/R, analyst view, risk/volatility, official VK IR news, MOEX fundamental snapshot, detailed VK fundamental analysis and valuation.

Valuation UX answers first: **НЕДООЦЕНЕНА / СПРАВЕДЛИВО ОЦЕНЕНА / ПЕРЕОЦЕНЕНА**, then current price, base value, margin/potential and Bear/Base/Bull EV/EBITDA evidence. It is analytical context, not a trading signal.

TradingView architecture decision (2026-09-29): the production chart uses the free public Advanced Chart Widget iframe. Its documented embed configuration supports adding studies but does not expose the Advanced Charts library API needed to create two Moving Average instances with independent length inputs. Therefore RSI14 remains inside TradingView; MA50/MA200 remain the deterministic MOEX H1 trend-context block above it. Do not reintroduce MA9, use unsupported embed overrides, or claim MA50/MA200 are TradingView overlay lines. Revisit only if the project adopts the separate Advanced Charts library/API.

## Fundamental analysis
Read-only official VK IR evidence layer. Current v1 is tied to the latest implemented official reporting release and fails closed when source validation fails. It does not change strategy gates.

## Evidence / audit
- S1 Decision Audit exists and deduplicates unchanged states.
- S4 H1 Decision Audit: `strategy4_h1_decision_audit.jsonl`, independent, deduplicated.
- Structural H1 S/R is read-only and does not alter S4 trigger semantics.
- Never reconstruct missing historical evidence.

## Known completed milestones
PR #125 H1 structural S/R; #126 zone-side fix; #127 fundamental analysis; #136/#137 TradingView sizing; #138-#143 TradingView study experiments/fixes including MA9 removal; #144 H1 MA50/MA200 trend context; #145 readable valuation indicator.

## Remaining work
1. Accumulate real S4 H1 evidence and compare with S1 only after adequate sample.
2. Do not promote S4 from SHADOW or tune H1 parameters from a tiny sample.
3. Replace source-bound fundamental v1 with robust official VK IR report parsing/history.
4. Add/maintain explicit fail-closed tests for fundamental source failure.
5. Improve mobile layout for new fundamental/valuation sections if production smoke shows issues.
6. TradingView MA50/MA200 overlay is CLOSED as a public-embed limitation; revisit only with the separate Advanced Charts library/API.
7. Audit historical S1 TP ordering anomaly only as data-integrity work under freeze.

## Release policy
Branch -> smallest scoped change -> tests/CI -> PR -> merge after relevant gates -> production verification. Preserve Strategy #1 freeze and fail closed on missing critical data.

## New-chat recovery
Read this file, fetch fresh main and Actions, inspect current public/live state, preserve S1 freeze, then continue only authorized VKCO work. Maximum simplicity; capital preservation; no invented data; evidence before release claims.
