# R1.4.3 — Entry Quality & Stop Engine

Status: IN TEST

## Goal
Turn the validated 1H Trend + Trigger candidate into a manageable trade without changing the R1.4.2 entry signal.

Core remains:
QUALITY → TREND → CLOSED-BAR TRIGGER → ENTRY

R1.4.3 adds only post-signal analytics:
ENTRY → INITIAL STOP → INVALIDATION → FORWARD PATH

## Point-in-time rules
- Signal is known only after the trigger 1H candle closes.
- Historical executable entry is the next 1H open.
- No intrabar look-ahead.
- Stops use only information available at signal time.
- Missing bars/invalid OHLC => N/A, never synthetic PASS.

## Stop candidates to test
A. SIGNAL_CANDLE: LONG below trigger-candle low; SHORT above trigger-candle high.
B. ATR_1_0: entry ± 1.0 × ATR14.
C. ATR_1_5: entry ± 1.5 × ATR14.
D. SWING_3: LONG below lowest low of last 3 completed candles; SHORT above highest high.

ATR14 uses Wilder smoothing. Stops are analytical candidates, not yet production recommendations.

## Forward horizons
For every R1.4.2 ENTRY event calculate directional return at 1H / 2H / 4H / 8H and path statistics:
- MFE
- MAE
- stop-hit rate per candidate
- survival rate
- return conditional on survival

## Gate
Do not select a universal stop because of one aggregate winner.
A stop can advance only if:
1. candidate count is adequate;
2. performance is not concentrated in one instrument;
3. stop-hit rate and MAE/MFE are economically coherent;
4. result is stable across time slices;
5. no material deterioration versus no-stop forward baseline.

Instrument-specific stops are allowed only after sufficient sample size. Otherwise keep the common baseline or N/A.

## Dashboard target
Do not alter ENTRY/CONFIRMED/LATE/WAIT/AVOID semantics in this release.
After validation, row/detail may add:
- Вход
- Стоп (candidate/validated)
- ATR14
- риск до стопа
- срок жизни сигнала
- отмена сигнала

## Non-goals
- no take-profit optimization yet;
- no trailing stop;
- no position sizing optimization;
- no OI/FUTOI substitution;
- no restoration of old mandatory R/R≥2 veto.
