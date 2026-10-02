# VKCO PROJECT CHECKPOINT

**Checkpoint date:** 2026-09-30 (Europe/Moscow)
**Project:** VKCO Trade Monitor + Control Room
**Repository:** YaDragon44/moex-crash-radar
**Status:** MANUAL OBSERVATION / STRATEGY #1 FREEZE

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
Read-only official VK IR evidence layer. Official VK IR release values are parsed from source; required-field or source validation failure returns DATA_UNAVAILABLE. It does not change strategy gates.

## Evidence / audit
- S1 Decision Audit exists and deduplicates unchanged states.
- S4 H1 Decision Audit: `strategy4_h1_decision_audit.jsonl`, independent, deduplicated.
- Structural H1 S/R is read-only and does not alter S4 trigger semantics.
- Never reconstruct missing historical evidence.

## Canonical documents
- `README.md` — operator overview.
- `REQUIREMENTS.md` — current baseline requirements.
- `ARCHITECTURE.md` — current component/data-flow architecture.
- `TASK_STATUS.md` — done/observe/next.
- `FINAL_COMPLETENESS_REVIEW.md` — development completion boundary.
- `RECOVERY_POINT_2026-09-30.md` — restore anchor.

## Known completed milestones
PR #125 H1 structural S/R; #126 zone-side fix; #127 fundamental analysis; #136/#137 TradingView sizing; #138-#143 TradingView study experiments/fixes including MA9 removal; #144 H1 MA50/MA200 trend context; #145 readable valuation indicator; #146 H1 Decision Audit + checkpoint sync; #147 fundamental fail-closed/mobile; #148 VK IR parser; #149 TradingView architecture decision; #150 LONG target-order safety.

## Remaining work\n1. Observe and accumulate S1 evidence: 10 trades diagnostic; prefer 20 before tuning.\n2. Accumulate S4 H1 evidence; keep SHADOW until adequate review.\n3. Maintain VK IR parser if official source format changes; fail closed meanwhile.\n4. Build comparative S1/S2/S3/S4 report only when sample is adequate.\n5. Hotfix only confirmed runtime/data-integrity/risk-safety defects during freeze.\n\n## Release policy
Branch -> smallest scoped change -> tests/CI -> PR -> merge after relevant gates -> production verification. Preserve Strategy #1 freeze and fail closed on missing critical data.

## New-chat recovery
Read this file, fetch fresh main and Actions, inspect current public/live state, preserve S1 freeze, then continue only authorized VKCO work. Maximum simplicity; capital preservation; no invented data; evidence before release claims.


## Manual-only decision — 2026-10-02
Owner decision: all VKCO automation and Telegram delivery are stopped. The VKCO workflow has no schedule/push trigger and runs only via manual workflow_dispatch. Automatic vkco-live publication is disabled. Telegram is hard-disabled for manual workflow runs. Analysis is initiated manually by the owner.
