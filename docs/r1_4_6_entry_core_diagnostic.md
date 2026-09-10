# R1.4.6 — Entry Core Diagnostic & Redesign

## Reason
R1.4.5 passed its technical gate but the frozen simple strategy failed the investment gate on OOS: mean after 5 bps -13.74 bps, PF 0.638, only 27.27% of tested families positive; NG -48.06 bps.

## Objective
Diagnose where the negative edge originates before adding indicators or optimizing parameters.

## Frozen evidence
Do not alter R1.4.5 trades while diagnosing them. No RSI, RVOL, OI, FUTOI, news, sentiment or ML rescue filters.

## Diagnostic cuts
For IS / Validation / OOS and especially OOS after 5 bps:
1. LONG vs SHORT.
2. Family/instrument.
3. Calendar quarter and month.
4. Signal hour.
5. Stop vs time exit.
6. MAE/MFE distributions in bps and ATR units.
7. Trigger strength = distance of signal close beyond previous high/low normalized by ATR.
8. Trend strength = EMA20-EMA50 spread normalized by ATR.
9. Entry gap = next-open vs signal close normalized by ATR.
10. Concentration: contribution of best/worst families and periods to aggregate P&L.

## Questions
A. Is the failure directional (LONG or SHORT)?
B. Is it concentrated in a few families such as NG?
C. Does the trigger have no continuation edge after the next open?
D. Is next-open execution destroying signal-close edge?
E. Is ATR1.5 stop truncating winners, or is the entry itself weak?
F. Is the 8H horizon wrong, or is expectancy already negative before exit design?

## Redesign discipline
Only after diagnostics, define at most 3 simple alternatives. Each alternative must change one conceptual component only and be specified before seeing its OOS result. No parameter grid search.

Candidate families of changes (not yet approved as strategies):
- Trigger redesign: breakout + hold/retest rather than one-bar breakout.
- Trend redesign: higher-timeframe structure confirmation rather than more oscillators.
- Execution redesign: avoid adverse next-open gap / require executable proximity to trigger.

## Gate
R1.4.6 diagnostic itself is PASS when all cuts are reproducible and identify whether failure is broad or concentrated. A redesigned entry core can advance only if it later shows positive Validation and OOS after 5 bps, PF > 1, adequate sample, and broad time/instrument stability. Production remains NO-GO until then.
