# VKCO RECOVERY POINT — 2026-09-30

## Identity
Repository: `YaDragon44/moex-crash-radar`
Scope: VK / VKCO only.
Baseline: after merged PR #150; documentation consolidation follows this recovery point.
Engine: R1.8.
Phase: MANUAL OBSERVATION / STRATEGY #1 FREEZE.

## Restore procedure
1. Fetch fresh `main`.
2. Read `vkco-monitor/PROJECT_CHECKPOINT.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`, `TASK_STATUS.md`, and this file.
3. Inspect latest Actions and public/live status before claiming runtime health.
4. Preserve S1 freeze and independent S2/S3/S4 state.
5. Do not reconstruct missing historical evidence.
6. Fix confirmed runtime/data-integrity/risk-safety defects immediately; otherwise observe.
7. Do not tune S1 from <20 closed model trades; 10 is diagnostic only.
8. Keep S4 SHADOW until adequate evidence and explicit review.

## Frozen S1
M10; Adaptive Wyckoff Spring + Adaptive Breakout/Hold; adaptive 20 completed candles excluding latest 3 trigger candles; RVOL breakout >=1.20, spring >=1.30; IMOEX + official VK IR event-risk mandatory; risk 0.5%.

## Current research
S2: M10 EMA50/EMA200 SHADOW.
S3: M10 RSI14 + valuation + EMA200 SHADOW.
S4: H1 S1-derived SHADOW; local/structural S/R; H1 MA50/MA200 context; independent lifecycle/journal/audit.

## Safety invariants
No broker orders. Missing critical evidence fails closed. New LONG model position requires `stop < entry < TP1 < TP2 < TP3`. Historical journal records are immutable.

## UI / evidence
Dashboard: `web/vkco-dashboard/index.html`.
TradingView: public H1 + RSI14 only. MA50/MA200 are MOEX H1 context outside iframe.
Fundamentals: official VK IR parser, fail-closed.
Valuation: read-only EV/EBITDA scenarios, not a trade signal.

## Next milestone
Observation, not feature expansion. At 10 S1 closed model trades perform diagnostic review; prefer 20 before any tuning decision. Compare S1/S2/S3/S4 only when sample is adequate.


## Manual-only decision — 2026-10-02
Owner decision: all VKCO automation and Telegram delivery are stopped. The VKCO workflow has no schedule/push trigger and runs only via manual workflow_dispatch. Automatic vkco-live publication is disabled. Telegram is hard-disabled for manual workflow runs. Analysis is initiated manually by the owner.
