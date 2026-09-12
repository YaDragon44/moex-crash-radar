# VKCO Monitor R1.6 — Trade Journal

## Goal
Persist every completed model position and calculate simple performance statistics without a database or broker integration.

## Added
- idempotent JSONL journal in the existing state cache;
- CSV export for manual review;
- completed-trade record: Ticker, Direction, Signal ID, Open/Close time, Entry, Exit, Shares, P/L, Result R, Setup, Score, Reason;
- Win Rate;
- Average R;
- Profit Factor;
- Expectancy in R;
- Telegram journal summary when a model position closes.

## Rules
- only completed model positions enter the journal;
- one close event can be written only once;
- statistics never mix active and completed trades;
- no broker integration and no auto-trading;
- R1.5 position-management rules remain unchanged.

## Persistence
Journal files are stored inside `vkco-monitor/state/` and therefore persist through the existing GitHub Actions cache together with position state.

## Production gate
PR regression PASS → merge → main production workflow PASS.
