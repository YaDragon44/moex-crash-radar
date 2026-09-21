# VKCO Monitor — Current Production Overview

A minimal cloud model/paper trading monitor for VKCO on MOEX.

## Current state
- Trading engine baseline: **R1.8**.
- Dashboard source: **R0.6.4**.
- Status: **PRODUCTION OBSERVATION / STRATEGY FREEZE**.
- R1.8.1 Risk Safety Hotfix is **not released** until all relevant gates pass.

Canonical documents:
- `REQUIREMENTS.md` — current requirements.
- `ARCHITECTURE.md` — current architecture.
- `PROJECT_CHECKPOINT.md` — recovery/status checkpoint.
- release documents — historical evidence, not the current requirements baseline.

## What it does
```text
MOEX M10
 -> Adaptive Spring / Breakout
 -> RVOL
 -> IMOEX filter
 -> VK IR Event Risk Lite
 -> Trade Plan
 -> Model Position
 -> Journal
 -> Telegram + sanitized Live State + read-only Dashboard
```

The system does **not** send broker orders.

## Strategy
Fixed historical VKCO price zones from R1.0 are obsolete.

Current production signals use adaptive support/resistance from completed M10 candles:
- Adaptive Breakout + Hold with RVOL confirmation.
- Adaptive Spring with reclaim/hold and RVOL confirmation.
- IMOEX and Event Risk gates are mandatory for READY.

Exact canonical rules are in `REQUIREMENTS.md` and `R1.2_SIGNAL_MODEL.md`.

## Risk
Production risk configuration remains 0.5% per model trade.

R1.8.1 is being developed to harden sizing with:
- official MOEX LOTSIZE;
- available-capital/notional cap;
- fail-closed invalid sizing metadata.

Until that release passes all relevant gates and is merged, it must not be described as production.

## Operations
GitHub Actions runs the monitor without a local computer or VPS. Scheduling is best-effort and intentionally offset from M10 candle boundaries.

Required secrets/variables must be configured only in repository settings. Never store tokens in code, docs, issues, public state or logs.

## Observation freeze
Do not change signal thresholds, RVOL, IMOEX, event-risk, Stop/TP or risk percentage before evidence:
- 10 closed model trades: diagnostic review;
- prefer 20 closed model trades before strategy tuning.

Safety/data/runtime defects may be hotfixed.

## Dashboard
The public dashboard is read-only and consumes sanitized VKCO Live State. It must fail visibly when data is unavailable and must never fabricate candles or status.

## Simplicity
No VPS, DB, Docker, Cloudflare, broker API, auto-trading, ML signal service or additional backend is required for the current scope.
