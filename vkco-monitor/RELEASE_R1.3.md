# VKCO Monitor R1.3 — Event Risk Lite

## Goal
Add a minimal event-risk gate before READY without creating a separate news service.

## Architecture
GitHub Actions → MOEX ISS → Adaptive VKCO Trigger → IMOEX Filter → Official VK IR Event Risk → Telegram.

## Source
Official VK investor news page: https://vk.company.ru/ru/investors/info/

## Logic
- Event check runs only after a technical signal and market filter pass.
- Window: today + previous 3 calendar days.
- Material keywords: results/reporting, dividends, bonds/debt, sanctions/restrictions, board decisions, placements, deals, buybacks, issuance, conversion, reorganization.
- Fresh material VK IR news blocks READY and produces WAIT / EVENT_RISK.
- If official VK IR is unavailable, READY is blocked as WAIT / EVENT_DATA_UNAVAILABLE.
- Telegram warning is de-duplicated through the existing state cache.
- Neutral IR/news items do not block READY.

## Preserved
- adaptive 20-candle levels;
- RVOL confirmation;
- IMOEX filter;
- heartbeat/failure alerts;
- anti-duplicate state;
- no broker access / no auto-trading;
- no VPS, Cloudflare, DB or external news API.

## Current known context as of 2026-09-12
- Official VK IR published on 2026-09-11 that VK plans a RUB 5bn bond placement to optimize debt structure without increasing debt.
- H1 2026 materials state that EU restrictive measures were applied in July 2026; VK said it did not expect a material operational impact and retained 2026 EBITDA guidance above RUB 24bn.

## Gate
PR regression PASS → merge → production workflow PASS → official VK IR live-source smoke PASS.
