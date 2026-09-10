# R1.4.7.1 — R3 Robustness Diagnostic

## Evidence
R1.4.7 R3 STRUCTURE+EARLY was the only positive hypothesis at the primary 4H/5bps view: Validation +1.36 bps (n=29, PF 1.054), OOS +17.51 bps (n=15, PF 1.818), but median OOS -9.54 bps, positive rate 40%, and no adequately sampled family breadth. It remains NO-GO due insufficient sample/concentration risk.

## Objective
Determine whether R3 is a repeatable regime-transition effect or a small-number/outlier artifact. Do not change R3 rules.

## Frozen R3
Same completed-bar intersection from R1.4.7: R1 price-structure transition AND R2 early-trend transition on the same bar. Same historical chain, splits, 1/2/4/8H forward returns and 5 bps primary research cost.

## Required diagnostics
For 4H R3 events report every Validation and OOS observation; family, side, quarter/month, gross/net return. Report LONG vs SHORT; family; quarter; top/bottom event concentration; contribution of top 1/top 3 winners to total positive P&L; leave-one-family-out and leave-one-event-out sensitivity; median and trimmed mean where sample permits.

## Robustness gate
R3 can remain a RESEARCH_CANDIDATE only if:
- Validation and OOS aggregate mean after 5 bps remain >0;
- OOS PF >1;
- no single event contributes >50% of total positive OOS P&L;
- removing the best OOS event does not turn OOS mean <=0;
- at least two independent families and both chronological subperiods contribute positive evidence where sample permits.
Otherwise R3 is REJECTED as non-robust.

No production promotion is possible in R1.4.7.1 regardless of outcome. If it survives, the next step is sample extension / market-specific validation, not Entry optimization.
