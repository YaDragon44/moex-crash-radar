# VKCO Monitor — Architecture v2.0

**Status:** CANONICAL  
**Architecture goal:** minimum components required for reliable model/paper monitoring.

## E2E

```text
MOEX ISS
   |
   v
monitor.py
   |
   +-- Adaptive Spring / Breakout
   +-- RVOL
   +-- IMOEX filter
   +-- VK IR Event Risk Lite
   |
   v
trade_plan.py
   |
   v
position_manager.py
   |
   +--> trade_journal.py --> weekly_review.py
   |
   +--> Telegram
   |
   +--> export_status.py --> sanitized vkco-live/status.json
                              |
                              v
                       GitHub Pages dashboard
```

## Runtime
GitHub Actions is the scheduler/runtime. No continuously running server is required.

## Data ownership
- MOEX ISS: market candles and official security metadata.
- VK official IR: limited corporate event-risk source.
- GitHub Actions cache/state: intentionally minimal model-position/journal persistence.
- `vkco-live/status.json`: sanitized public delivery state, not the trading system of record.

## Boundaries
Trading decisions are produced only by the accepted Python engine. The dashboard is a read-only projection and must not create or modify signals.

Telegram is notification-only. There is no broker execution integration.

## Simplicity lock
Do not add a database, API server, message bus, container platform, VPS, broker connector or second market-data pipeline unless a documented requirement cannot be satisfied by the current architecture.

## Production entry
R1.8 uses `run_r18.py` as the operational wrapper over the accepted engine. Do not create a new version wrapper merely for documentation/UI/safety changes unless runtime behavior genuinely requires it.

## Current release state
- Trading engine accepted production baseline: R1.8.
- Dashboard accepted source release: R0.6.4.
- R1.8.1 Risk Safety Hotfix: development only until every relevant gate passes.
