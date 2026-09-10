# R1.4.6.1 — LONG Entry Redesign

## Evidence
R1.4.6 OOS diagnostic after 5 bps: LONG -27.31 bps/trade; SHORT +0.01 bps/trade; NG -48.06 bps; broad_failure=true.

## Objective
Test whether the LONG defect comes from buying immediately after a one-bar breakout. Do not add indicators and do not alter SHORT.

## Frozen common rules
1H; same EMA20/EMA50 trend definition; Wilder ATR14; protective reference 1.5 ATR; fixed 8 completed bars maximum hold; next-bar-open execution; same historical roll-chain and IS/Validation/OOS splits; 5 bps primary cost.

## Variants
### L0 CONTROL
Existing LONG: completed close > previous completed high; enter next bar open.

### L1 BREAKOUT_HOLD
Bar t closes above high(t-1). Bar t+1 must also close above the original breakout level high(t-1), while LONG trend remains valid at t+1. Entry = open(t+2). No intrabar assumption.

### L2 BREAKOUT_RETEST
Bar t closes above high(t-1). On bar t+1, low <= original breakout level AND close > original breakout level, with LONG trend still valid at t+1. Entry = open(t+2). This is a completed-bar retest only; no intrabar execution claim.

SHORT remains the R1.4.5 control in all portfolio comparisons.

## Anti-overfit rules
No threshold tuning, no EMA/ATR grid, no RSI/RVOL/OI/FUTOI. Compare exactly L0/L1/L2. Primary verdict uses Validation and OOS after 5 bps, sample size, PF, positive family/quarter share, DD/recovery and concentration.

## Gate
A LONG variant is a candidate only if OOS mean after 5 bps > 0, PF > 1, Validation is not materially contradictory, sample is meaningful, and improvement is not dominated by one family/quarter. Otherwise LONG remains NO-GO.
