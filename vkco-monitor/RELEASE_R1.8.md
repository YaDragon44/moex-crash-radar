# VKCO Monitor R1.8 — Production Audit / Simplification

## Goal
Simplify production operations without changing trading logic.

## Audit findings
1. Regular 10-minute cron overlapped the 10:00 MSK heartbeat.
2. Regular runs started exactly on candle boundaries, increasing the chance of reading a candle before finalization.
3. Heartbeat always reported OK even when MOEX data was stale.
4. Three obsolete R1.1 service files remained in the production folder.
5. Release history is useful and must be preserved.

## Changes
- Regular cron shifted to `3,13,23,33,43,53 6-20 * * 1-5` UTC.
- Heartbeat remains `0 7 * * 1-5` UTC (10:00 MSK).
- Added thin `run_r18.py` operational wrapper; trading engine remains unchanged.
- Heartbeat now reports:
  - `HEARTBEAT OK` only for same-day data not older than 45 minutes;
  - `HEARTBEAT DEGRADED` otherwise.
- Manual Telegram smoke text updated to R1.8.
- Failure alert updated to R1.8.
- Removed obsolete `.r1_1_gate`, `README_R1_1.md`, `STATUS_R1_1.md`.

## Preserved
- Adaptive VKCO setup engine;
- RVOL;
- IMOEX filter;
- official VK IR Event Risk Lite;
- Trade Plan and risk sizing;
- Position Management;
- Trade Journal;
- Weekly Review;
- existing state/cache model;
- no VPS, DB, Docker, Cloudflare, broker API or auto-trading.

## Known intentional limitations
- GitHub Actions cron is best-effort and may start late.
- Event Risk remains Lite and checks official VK IR only.
- Model positions are not broker-confirmed positions.
- State uses GitHub Actions cache rather than a database by design.

## Complexity verdict
Architecture remains intentionally simple: GitHub Actions + Python + MOEX ISS + VK IR + Telegram.
No new infrastructure added.

## Production gate
PR regression PASS → merge → main production run PASS.
