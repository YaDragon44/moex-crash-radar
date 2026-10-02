# VKCO Trade Monitor + Control Room — R1.8

Production observation system for VK / VKCO only.

## Purpose
Read-only market/evidence monitoring and model-position research. No broker API and no automatic orders.

## Architecture
`GitHub Actions -> MOEX ISS -> S1/S2/S3/S4 -> evidence/risk gates -> model lifecycle/journals -> sanitized status -> GitHub Pages + Telegram`

## Strategies
- S1: primary/frozen, M10 Adaptive Wyckoff Spring + Breakout/Hold.
- S2: SHADOW M10 EMA50/EMA200 benchmark.
- S3: SHADOW M10 RSI14 + valuation + EMA200 regime.
- S4: SHADOW H1 S1-derived research strategy with local/structural S/R and H1 MA50/MA200 trend context.

S1 production gates: adaptive 20 completed M10 candles excluding latest 3 trigger candles; RVOL breakout >=1.20, spring >=1.30; IMOEX mandatory; official VK IR event-risk mandatory; risk 0.5%.

## Evidence
S1 and S4 have independent deduplicated Decision Audit logs. Model positions and trade journals are not broker executions. New LONG positions fail closed unless `stop < entry < TP1 < TP2 < TP3`.

## Fundamentals / valuation
Official VK IR fundamental data is parsed automatically and fails closed on missing required fields. Valuation is read-only EV/EBITDA scenario analysis and is not a trade signal.

## Dashboard
Production UI: `web/vkco-dashboard/index.html`. TradingView public widget: H1 + RSI14. MA50/MA200 are deterministic MOEX H1 context outside the iframe because the public widget does not expose the separate Advanced Charts library API required for independently parameterized MA overlays.

## Operating mode
Strategy #1 remains frozen under issue #61. 10 closed model trades = diagnostic review; prefer 20 before tuning. S4 remains SHADOW until adequate evidence exists. Runtime/data-integrity/risk-safety defects may be hotfixed immediately.

## Recovery
Canonical recovery instructions: `vkco-monitor/RECOVERY_POINT_2026-09-30.md`.
Current state: `vkco-monitor/PROJECT_CHECKPOINT.md`.


## Manual-only decision — 2026-10-02
Owner decision: all VKCO automation and Telegram delivery are stopped. The VKCO workflow has no schedule/push trigger and runs only via manual workflow_dispatch. Automatic vkco-live publication is disabled. Telegram is hard-disabled for manual workflow runs. Analysis is initiated manually by the owner.
