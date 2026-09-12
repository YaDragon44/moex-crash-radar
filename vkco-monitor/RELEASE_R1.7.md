# VKCO Monitor R1.7 — Weekly Review

## Goal
Add a simple weekly Telegram review based on the existing R1.6 trade journal, without a database, broker integration, or new services.

## Schedule
- Monday 08:05 MSK (`5 5 * * 1` UTC).
- Separate GitHub Actions workflow from the 10-minute trading monitor.

## Weekly report
- completed model trades over the last 7 days;
- W/L and Win Rate;
- weekly P/L RUB;
- Average R;
- Profit Factor;
- Expectancy R;
- best/worst trade in R;
- best/weak setup by average R when data exists;
- total journal sample size;
- simple action rule.

## Guardrails
- no strategy change when weekly sample is below 3 trades;
- negative Expectancy => do not increase risk;
- zero-trade week => short status only;
- read-only use of existing journal cache;
- no broker integration and no auto-trading.

## Architecture
GitHub Actions weekly workflow → existing cached trade journal → weekly_review.py → Telegram.

## Production gate
PR regression PASS → merge → main push preview PASS → scheduled/manual Telegram delivery.
