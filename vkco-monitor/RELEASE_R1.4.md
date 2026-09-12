# VKCO Monitor R1.4 — Trade Plan

## Goal
Add position sizing and monetary risk to READY messages without changing the R1.3 signal engine.

## Architecture
GitHub Actions → MOEX ISS → VKCO adaptive trigger → IMOEX filter → VK IR Event Risk → Trade Plan → Telegram.

## Added
- `trade_plan.py` isolated sizing layer;
- `run_r14.py` thin wrapper over the accepted R1.3 core;
- GitHub Variables `TRADING_CAPITAL_RUB` and `RISK_PCT`;
- allowed monetary risk, per-share risk, shares/lots, position value, actual risk;
- safe fallback when sizing variables are not configured;
- regression tests for sizing and invalid stop.

## Not added
No broker integration, order placement, database, VPS, Cloudflare or auto-trading.

## Gate
PR regression PASS → merge → main production PASS.
