# TA Market Monitor — QA Baseline

## Mandatory gates
1. Snapshot JSON parses and quality == OK.
2. SBERP, VKCO, OZPH exist.
3. D1/H1/M10 data exists for production analysis.
4. LOTSIZE is valid for all instruments.
5. IMOEX exists.
6. context_quality == OK and context_errors is empty for production publication gate.
7. Breadth, CNY/RUB and Brent exist; Brent has SECID.
8. Signal History events obey ticker/timeframe/status contract.
9. Performance metrics are non-negative and result is WIN/LOSS/OPEN/AMBIGUOUS.
10. Sample Quality matches closed count.
11. Telegram state has baseline and deduplication list.
12. Public Pages JSON/history/performance/UI health checks pass.

## Regression locks
- READY must never bypass closed/fresh candle, trigger, momentum, RVOL, targets, R/R or market veto.
- R/R threshold remains >=2.
- RVOL threshold remains >1.1x.
- Same snapshot must not change signal state merely because a GitHub runner starts later.
- No tuning while Sample Quality is INSUFFICIENT.

## Current observation
At the 2026-09-21 audit, signal_performance reports 0 READY and 0 closed, therefore Sample Quality is INSUFFICIENT. This is an evidence limitation, not a QA failure.

## Next QA
Add explicit session-state tests for market closed / last session versus genuine stale-data failure, without changing READY eligibility.

## R0.9.2.4 acceptance
- Outside the configured Moscow trading window, an old last candle is displayed as LAST SESSION, not as a data-quality incident.
- During the trading window, an over-age candle remains STALE.
- LAST SESSION does not make READY eligible: the existing fresh=false safety condition is unchanged.
- Snapshot wall-clock freshness <=25m remains unchanged in production_patch.js.
