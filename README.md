# MOEX Crash Early Warning Radar

Система раннего предупреждения обвала российского рынка акций и поиска подтверждённого дна для обратного набора позиций.

## Current release
R0.4.2 — Approved UI Implementation (IN TEST)

## Architecture
Static frontend + GitHub Pages + GitHub Actions + public market/macro data sources. No dedicated backend.

## Core engines
- Crash Score 0–100
- Crash Momentum
- Bottom Score 0–100
- EXIT/CASH state machine
- BUY-BACK state machine
- Data Quality: LIVE / DELAYED / STALE / ERROR / N/A
- Historical backtest and calibration

## R0.3.1 first real evidence run
MOEX ISS range: 2019-09-01 → 2026-08-27. Point-in-time features, no look-ahead.

Detected configured episodes:
- COVID 2020: CASH 2020-02-25 → trough 2020-03-18, lead 22 calendar days; episode drawdown -32.37%
- Feb 2022: CASH 2022-01-14 → trough 2022-02-24, lead 41 days; drawdown -44.95%
- Sep 2022: CASH 2022-08-03 → trough 2022-10-10, lead 68 days; drawdown -12.07%
- 2024 correction: CASH 2024-05-27 → trough 2024-09-03, lead 99 days; drawdown -26.68%

The broad 2025–2026 window generated an excessively early signal and is not considered a clean standalone crash episode for threshold validation.

### Important finding
The legacy **day-level** false-positive metric was 66.12% (162 false CASH days out of 245 evaluable CASH days). This is too high for a production exit signal and also over-counts persistent risk regimes as repeated alerts.

Therefore R0.3.1 is **not accepted yet**. Event-level calibration was added: one continuous warning regime = one event, with combinations of score threshold / critical confirmations / persistence. Release Gate: representative crash episodes detected, false-event rate ≤35%, median lead ≥5 calendar days.

### Backtest limitation
Breadth currently uses a present-day liquid basket, not historical index constituents. Historical results have survivorship/listing-history bias and are calibration evidence, not unbiased production performance.

## Dashboard
R0.4.2 implements the approved one-screen UI in `web/index.html`: 9 indicator cards, Crash Score, EXIT/CASH, Bottom Score, Crash Momentum, data-status badges, and the three strongest available signal groups behind the current action. The UI preserves strict N/A/ERROR behaviour; it never invents a missing market or macro value.

Missing or stale source data must never be replaced with invented values. The system returns DATA INSUFFICIENT when required evidence is unavailable.
