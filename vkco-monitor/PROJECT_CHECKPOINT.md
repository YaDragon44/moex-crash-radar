# VKCO PROJECT CHECKPOINT

**Checkpoint date:** 2026-09-21 (Europe/Moscow)  
**Project:** VKCO Trade Monitor + Control Room  
**Repository:** YaDragon44/moex-crash-radar  
**Status:** PRODUCTION OBSERVATION / STRATEGY FREEZE

## 1. Recovery anchor

Use this file as the canonical recovery point for the VKCO project. Do not reconstruct VKCO state from other dashboards/projects in this repository.

Dashboard accepted source release: **R0.6.4 UI Recovery Hotfix**, merged via PR #80, commit `61d68f1b7df5f7577dfcf77bb7acbfffd1fcac7a`.\n\nCanonical requirements: `vkco-monitor/REQUIREMENTS.md`. Canonical architecture: `vkco-monitor/ARCHITECTURE.md`.

The repository may contain later automated/data-only commits. Preserve this recovery anchor for the dashboard implementation and inspect current `main` before making new changes.

## 2. Production architecture

Keep architecture minimal:

`GitHub Actions -> MOEX ISS -> VKCO adaptive trigger -> IMOEX filter -> VK official IR event-risk -> trade plan -> model position management -> trade journal -> Telegram -> sanitized public Live State -> GitHub Pages dashboard`

No VPS, DB, Docker, Cloudflare, broker API or automatic broker orders.

Production trading engine release: **R1.8**.  
Dashboard source release: **R0.6.4**.

## 3. Production links

- Dashboard: `https://yadragon44.github.io/moex-crash-radar/vkco-dashboard/`
- Cache-bypass dashboard: `https://yadragon44.github.io/moex-crash-radar/vkco-dashboard/?v=r064`
- VKCO monitor workflow: `https://github.com/YaDragon44/moex-crash-radar/actions/workflows/vkco-monitor.yml`
- Production observation issue: `https://github.com/YaDragon44/moex-crash-radar/issues/61`
- Source: `vkco-monitor/`
- Dashboard source: `web/vkco-dashboard/index.html`
- Public state: `https://raw.githubusercontent.com/YaDragon44/moex-crash-radar/vkco-live/status.json`

## 4. Accepted production state

R1.8 production audit is accepted. Regular monitor runs are offset from M10 candle boundaries; heartbeat validates data freshness instead of returning unconditional OK. Stable position/journal logic remains unchanged.

R0.6.2 changed the public Live State contract so `status.json` contains the latest **72 completed VKCO M10 candles**. The monitor regression reached **40/40 PASS** when this contract was introduced.

R0.6.3 rebuilt the dashboard as valid UTF-8 and removed the chart dependency on the large TA Market JSON. The dashboard now reads market/trade state and M10 candles from the single existing `vkco-live/status.json` source.

R0.6.3 was superseded by **R0.6.4 UI Recovery Hotfix** (PR #80, commit `61d68f1b7df5f7577dfcf77bb7acbfffd1fcac7a`). R0.6.4 replaced the corrupted/mojibake dashboard source with clean UTF-8 while preserving the single Live State contract.

Post-merge GitHub Pages run `34704730108` completed successfully:
- build: PASS;
- deploy: PASS;
- public-health-check: PASS.

The dashboard includes Price + Volume, 72 M10 candles, Support/Resistance, adaptive trade levels, VSA context, Wyckoff context, model lifecycle, risk, journal and health indicators.

## 5. Trading state / freeze

Production observation issue #61 is the governing freeze:
- do not change adaptive levels, RVOL thresholds, IMOEX filter, event-risk logic, stop/TP rules or risk percentage before sufficient model evidence;
- at **10 closed model trades** perform diagnostic review only;
- prefer **20 closed model trades** before evidence-based strategy tuning;
- runtime, data-integrity, duplicate/state-transition and risk-safety defects may be hotfixed immediately.

Current position semantics are **MODEL/PAPER**, not broker-confirmed execution. No automatic orders are sent.

## 6. Known limitations / safety backlog

These items are not permission to expand scope unnecessarily.

1. **VKCO LOTSIZE correctness:** trade sizing must use current official MOEX LOTSIZE; do not rely blindly on default `lot_size=1`.
2. **Capital/notional cap:** for no-leverage sizing, shares must be capped by available capital as well as risk budget so a tight stop cannot create notional above capital.
3. Event-risk parser uses official VK IR only and is not comprehensive general-news/sanctions monitoring.
4. Model position opens from READY without broker fill confirmation; always label it model/paper.
5. Journal partial TP handling is simplified; actual manual partial exits are not reconstructed automatically.
6. Cache-backed journal/state is intentionally minimal and is not a durable database.

Items 1–2 are **risk-safety correctness** and may be implemented as `R1.8.1 Risk Safety Hotfix` without violating the strategy freeze.

## 7. Dashboard invariants

Do not claim chart/live data is available unless the public Live State actually contains valid candles.

Dashboard must:
- use `vkco-live/status.json` as the single VKCO live-state/chart source;
- show `M10 DATA UNAVAILABLE` / degraded state rather than fabricate data;
- show actual candle count (`N / 72`);
- clearly distinguish WAIT / READY / OPEN / TP1 / TP2 / TRAILING / CLOSED;
- clearly label model/paper position;
- never expose Telegram/GitHub secrets or raw secret environment values;
- remain read-only.

## 8. Release / QA policy

For every material change:
1. create a dedicated branch;
2. make the smallest scoped change;
3. run targeted tests + repository CI;
4. open PR with release notes;
5. merge only on green relevant gates;
6. verify production workflow/Pages deployment;
7. for dashboard changes verify the real public URL and public Live State, not only repository files;
8. remove temporary smoke/debug workflows after validation;
9. update this checkpoint after an important accepted release.

Do not report `FIXED` or `PRODUCTION READY` based only on source inspection. Public/UI issues require a public production gate.

## 9. NEXT TASK

**R1.8.1 — Risk Safety Hotfix**

Scope is strictly limited to risk-sizing correctness before the first real READY:
- fetch/verify official VKCO `LOTSIZE` from MOEX ISS;
- size position using both risk budget and available-capital/notional cap;
- preserve 0.5% production risk setting;
- add regression tests for LOTSIZE rounding, tight-stop notional cap, missing/invalid metadata and no-position fallback;
- do not change signal thresholds, adaptive levels, IMOEX filter, event-risk logic, stop/TP strategy or dashboard trading interpretation.

Current development PR: **#81**. Do not merge or describe R1.8.1 as production until every relevant VKCO gate is green. The implementation work covers official MOEX LOTSIZE, available-capital/notional cap and fail-closed sizing metadata; specialized regression remains the release authority.\n\nAfter accepted R1.8.1: return to **Production Observation** and collect model trades under issue #61. No strategy optimization before the evidence gate.

## 10. Recovery instruction

When recovering this project in a new chat:

1. Read `vkco-monitor/PROJECT_CHECKPOINT.md`, `REQUIREMENTS.md` and `ARCHITECTURE.md` first.
2. Inspect current `main` and confirm the recovery anchor/relevant later commits.
3. Read the production files only as needed for the NEXT TASK.
4. Do not reconstruct requirements from unrelated `moex-crash-radar` modules.
5. Execute only the NEXT TASK unless a production/risk-safety defect requires an immediate hotfix.
6. Preserve the principle: **maximum simplicity, capital preservation, no invented data, no strategy changes during the observation freeze.**
