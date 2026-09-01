# R1.4.4 — Exit & Trade Management

## Goal
Turn the Simple Entry Radar from an entry-only decision aid into a minimal trade lifecycle while preserving the validated R1.4.2 entry core.

**QUALITY → TREND → TRIGGER → ENTRY → RISK → MANAGEMENT → EXIT**

This release does not optimize for maximum profit. It tests whether simple, explainable management rules improve risk-adjusted behavior versus a fixed 8H hold.

## Entry contract
Unchanged from R1.4.2/R1.4.3:
- completed 1H bars only;
- directional EMA20/EMA50 trend;
- previous-bar high/low trigger;
- historical executable entry at next 1H open;
- ATR14 uses Wilder smoothing;
- ATR×1.5 remains a **candidate risk reference**, not a production-validated universal stop.

## Management candidates
All decisions are evaluated only at completed 1H bar boundaries unless the protective stop is touched intrabar.

### M0 — FIXED_8H
Baseline. Hold for 8 completed 1H bars, no management.

### M1 — ATR_STOP_1_5
Initial protective stop at 1.5×ATR14 from entry. Exit immediately if touched.

### M2 — BREAK_EVEN_AFTER_1R
Initial ATR×1.5 stop. Once favorable excursion reaches +1R, move stop to entry. No trailing beyond break-even. Exit at stop or after 8H.

### M3 — TREND_EXIT
Initial ATR×1.5 stop. At each completed 1H bar, exit if the entry trend loses its hard directional condition (EMA20/EMA50/slope/price relationship). Otherwise hold to 8H.

### M4 — HYBRID_SIMPLE
Initial ATR×1.5 stop; move to break-even after +1R; also exit on completed-bar trend invalidation. Otherwise exit at 8H.

## User-facing lifecycle states
- **HOLD** — setup remains valid; no management action.
- **PROTECT** — +1R achieved; break-even protection is allowed by the tested rule.
- **EXIT TREND** — directional trend invalidated on a completed 1H bar.
- **EXIT STOP** — protective stop touched.
- **TIME EXIT** — maximum tested signal life reached.
- **DATA N/A** — quality/chronology insufficient.

No PARTIAL EXIT is introduced in this release. It adds sizing complexity without evidence yet.

## Historical Gate
Compare M0–M4 on the same entry population. Required metrics:
- sample size;
- mean and median net bps;
- positive-trade rate;
- stop/trend/time exit mix;
- average holding time;
- MAE/MFE;
- cost sensitivity;
- stability by instrument and time slice;
- comparison with M0 fixed-hold baseline.

A management rule cannot become universal merely because aggregate mean return is highest. It must be stable across instruments/time slices and must not create unacceptable churn/cost sensitivity.

## Quality / anti-lookahead
- Entry uses next-bar open after the trigger close.
- Trend exits use completed bars only.
- Intrabar stop logic may use bar high/low but never assumes favorable execution beyond the stop price.
- If stop and +1R are both touched within the same bar and ordering is unknowable, use conservative ordering: stop first unless the prior completed bar had already armed break-even.
- Missing bars or invalid ATR => N/A.

## GO / NO-GO
**GO candidate** only if a simple management model:
1. has adequate sample;
2. remains positive after reasonable cost assumptions;
3. is stable across instrument/time cells;
4. improves downside/holding behavior without materially destroying expectancy;
5. has deterministic point-in-time semantics.

Otherwise retain the M0/M1 reference behavior and do not add complexity to the live radar.
