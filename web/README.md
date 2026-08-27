# R0.4 Dashboard MVP

`index.html` is the one-screen MOEX Crash Radar UI.

It consumes `market_snapshot.json` generated from real MOEX ISS data. Missing indicators render as `N/A`; failed snapshot load renders `ERROR`. No demo values are injected.

Production GitHub Pages deployment is intentionally gated by R0.3.1 calibration. Do not treat the current CASH gate as production-ready until the event-level false-positive / lead-time Gate passes.
