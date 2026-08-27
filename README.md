# MOEX Crash Early Warning Radar

Система раннего предупреждения обвала российского рынка акций и поиска подтверждённого дна для обратного набора позиций.

## Current release
R0.3.1 — Historical Evidence + Calibration (IN TEST)

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

## R0.3.1 evidence status
First real MOEX evidence run (2019-09-01 → 2026-08-27) completed successfully. It detected the configured crash/correction episodes, but the legacy **day-level** false-positive metric was 66.12%. That metric over-counts persistent risk regimes as repeated false alerts and therefore does **not** pass as a release-quality validation metric.

The next calibration pass evaluates **independent warning events** with threshold / confirmation / persistence combinations. Release Gate: detect all configured episodes, false-event rate ≤35%, median lead ≥5 calendar days. Until that Gate passes, CASH logic remains experimental.

## Dashboard
R0.4 one-screen dashboard scaffold is already in `web/index.html`. It never invents missing values: unavailable indicators render as `N/A` and missing snapshot as `ERROR`.

Missing or stale source data must never be replaced with invented values. The system returns DATA INSUFFICIENT when required evidence is unavailable.
