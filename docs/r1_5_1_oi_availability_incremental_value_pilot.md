# R1.5.1 — OI Data Availability & Incremental Value Pilot

## Objective
Before any new score or trading rule, determine whether point-in-time historical OI is actually available with enough depth/coverage to test incremental value over price.

Pilot families: MX, SI, SR, GZ. Keep the pilot small.

## Phase A — Availability Gate
For every candidate source/family record:
- source and exact field semantics
- first/last timestamp actually retrieved
- event_time / available_time semantics
- frequency
- contract coverage and gaps
- public/authenticated status
- quality = LIVE / DELAYED / STALE / N/A / BLOCKED_AUTH

No forward fill. No inferred historical OI. No daily FIZ/YUR substitute for intraday FUTOI.

## Phase B — Minimal ablation, only if Phase A passes
M0 = frozen price-only control.
M1 = M0 + OI participation features only.
FIZ/YUR remains excluded while FUTOI history is BLOCKED_AUTH.

OI features are descriptive and point-in-time: delta OI, delta OI %, rolling percentile, price×OI quadrant and persistence. Threshold +0.5% / P75 remains a hypothesis; primary pilot must report continuous/bucket diagnostics before any hard threshold promotion.

## Gate
DATA_READY only if historical OI has valid point-in-time semantics and sufficient coverage for at least two pilot families and at least two chronological subperiods. Otherwise DATA_LIMITED and M1 backtest is forbidden.

If M1 runs, incremental value must beat M0 on pre-defined transition/risk diagnostics without materially increasing false alarms. No production trading promotion in R1.5.1.

Production: NO-GO.
