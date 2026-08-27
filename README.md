# MOEX Crash Early Warning Radar

Система раннего предупреждения обвала российского рынка акций и поиска подтверждённого дна для обратного набора позиций.

## Current release
R0.3 — Crash Engine + Backtest

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

Missing or stale source data must never be replaced with invented values. The system returns DATA INSUFFICIENT when required evidence is unavailable.
