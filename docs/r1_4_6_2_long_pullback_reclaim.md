# R1.4.6.2 — LONG Pullback / Reclaim

## Evidence
R1.4.6.1 rejected the LONG breakout family. OOS after 5 bps: L0 breakout -27.31 bps (PF 0.349), L1 hold -29.84 (PF 0.281), L2 retest -43.82 (PF 0.134). Validation was negative for all three.

## Objective
Change only the LONG entry structure from momentum breakout to pullback/reclaim. Keep the system simple.

## Frozen common rules
1H. EMA20 > EMA50 and rising trend. Wilder ATR14. Next-bar-open execution. ATR1.5 protective reference. Maximum 8 completed 1H bars. Same roll-chain, IS/Validation/OOS and 5 bps primary cost. SHORT remains unchanged control.

## Variants
### P0 BREAKOUT CONTROL
Existing R1.4.5 LONG breakout: close(t) > high(t-1), entry open(t+1).

### P1 EMA20 TOUCH + RECLAIM
LONG trend valid at t. During completed bar t, low(t) <= EMA20(t) and close(t) > EMA20(t). Require previous completed close(t-1) > EMA20(t-1) so the event is a pullback from above, not a cross from below. Entry open(t+1).

### P2 EMA20 CLOSE-BELOW + RECLAIM
LONG trend context is valid before pullback. Bar t-1 closes <= EMA20(t-1), after at least one prior bar above EMA20. Bar t closes > EMA20(t), EMA20(t) > EMA50(t), EMA20 rising. Entry open(t+1). This is a completed-bar reclaim, not intrabar execution.

## Anti-overfit
Exactly P0/P1/P2. No EMA-period grid, ATR tuning, RSI, RVOL, OI, FUTOI, news, ML or discretionary filters.

## Candidate gate
LONG candidate only if Validation is non-negative, OOS after 5 bps > 0, OOS PF > 1, OOS n >= 100 where possible, and performance is not concentrated in one family/quarter. Otherwise LONG remains NO-GO.
