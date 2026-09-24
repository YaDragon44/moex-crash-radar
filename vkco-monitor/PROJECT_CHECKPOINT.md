# VKCO PROJECT CHECKPOINT

**Checkpoint date:** 2026-09-24 (Europe/Moscow)  
**Project:** VKCO Trade Monitor + Control Room  
**Repository:** YaDragon44/moex-crash-radar  
**Status:** PRODUCTION OBSERVATION / STRATEGY FREEZE

## Recovery anchor

This file is the canonical recovery point for the VKCO-only workstream. Always inspect fresh `main` before acting.

Production engine: **R1.8**. Dashboard accepted source baseline: **R0.6.4**, with later UI/log hotfixes.

## Architecture

`GitHub Actions -> MOEX ISS -> adaptive VKCO trigger -> IMOEX filter -> official VK IR event-risk -> trade plan -> model position manager -> journal -> Telegram + sanitized vkco-live/status.json -> GitHub Pages dashboard`

No broker API/orders, VPS, DB, Redis, Docker, Cloudflare or ML.

## Production paths

- Dashboard: `web/vkco-dashboard/index.html`
- Monitor: `vkco-monitor/monitor.py`
- Runtime: `vkco-monitor/run_r18.py`
- Trade plan: `vkco-monitor/trade_plan.py`
- Position lifecycle: `vkco-monitor/position_manager.py`
- Journal: `vkco-monitor/trade_journal.py`
- Public exporter: `vkco-monitor/export_status.py`
- Live branch/file: `vkco-live/status.json`
- Workflow: `.github/workflows/vkco-monitor.yml`
- Observation issue: #61

## Current production facts

- Trading strategy is frozen during Production Observation.
- Authorized LONG setups only: **Adaptive Wyckoff Spring** and **Adaptive Breakout + Hold**.
- Adaptive levels: previous 20 completed M10 candles, excluding the latest 3 trigger candles.
- RVOL threshold: breakout >= 1.20; spring >= 1.30.
- IMOEX market filter and official VK IR Event Risk Lite remain mandatory.
- Production risk setting remains 0.5%.
- Model/paper positions are not broker executions.
- Dashboard is read-only and consumes the sanitized live state.

## Dashboard / entry-log state

Dashboard recovery R0.6.4 is accepted and uses only `vkco-live/status.json` for VKCO live state and the 72 completed M10 candles.

2026-09-24 additions:
- PR #93 added bottom block **Entry setup & indicator log**.
- Public exporter now exposes a sanitized `entry_log` for up to 20 persisted model entries.
- Existing historical journal records show setup, opened/closed time, entry/exit, score, status and Result R.
- Historical RVOL, Support/Resistance, IMOEX filter and Event Risk snapshots were not persisted for the existing trade; UI must show them as **not saved**, never reconstruct/invent them.
- PR #94 removed the stray literal `\\n` visible between the entry-log and current-action cards.

Known persisted model trade at this checkpoint:
- setup: Adaptive Wyckoff Spring;
- opened: 2026-09-21T13:09:59+03:00;
- entry: 109.80;
- score: 10/19;
- journal result: +3.125R;
- stored terminal status: CLOSED_STOP.

The combination of profitable result with terminal label CLOSED_STOP and the persisted moved stop above entry requires lifecycle semantics inspection before interpreting it as a defect.

## Observability gap

The current journal persists completed model positions, not a complete decision history. Therefore it cannot prove how many candidate/blocked entry points existed.

Recommended next product slice is a minimal **Decision Audit Log** that persists future decision snapshots without changing strategy:
`timestamp -> candle -> WAIT/READY/BLOCKED -> reason -> setup -> support/resistance -> RVOL -> trigger facts -> IMOEX/SMA20/1h -> Event Risk -> score -> Entry/Stop/TP -> signal_id`.

Deduplicate unchanged states; do not log every identical heartbeat.

## Risk safety

R1.8.1 work exists separately and must remain safety-only:
- official current MOEX LOTSIZE;
- risk-budget sizing plus capital/notional cap;
- fail closed on missing/invalid metadata;
- no changes to signal thresholds or trading strategy.

Do not call R1.8.1 released unless its specialized gates are green and the relevant PR is merged.

## Production observation gate

Issue #61 governs the freeze:
- 10 closed model trades -> diagnostic review only;
- prefer 20 closed model trades before strategy tuning;
- runtime/data-integrity/state-transition/risk-safety defects may be fixed immediately.

Current public journal contains only **1 completed model trade**.

## QA / release policy

For every material change:
1. dedicated branch;
2. smallest scoped change;
3. targeted regression + repository CI;
4. PR;
5. merge only after relevant gates;
6. production workflow/Pages verification;
7. UI changes require real public-page verification;
8. no invented data;
9. update this checkpoint after accepted material changes.

## Current transition state

PR #93 is merged; merge commit `a62f47127687dbcdfc5faab866faed7de35d793d`. Its push runs for CI, VKCO Monitor, Live MOEX snapshot and Deploy Dashboard completed successfully.

PR #94 is merged; merge commit `579c0cc01006ed52fc025b2c4522a4e80f7e514e`. It is a presentation-only fix for the visible literal newline. At the moment of this checkpoint its post-merge CI/Deploy runs had just been queued; fresh status must be checked in the new chat before declaring the hotfix fully production-verified.

## New-chat recovery instruction

1. Read this file first.
2. Fetch fresh `main` and current Actions status.
3. Verify PR #94 deployment/public page if not already green.
4. Inspect current `vkco-live/status.json`.
5. Preserve strategy freeze.
6. Then continue the authorized next work only; do not reconstruct state from unrelated repository modules.
7. Principle: **maximum simplicity, capital preservation, no invented data, evidence before release claims.**
