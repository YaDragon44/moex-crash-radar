# R1.5.0 — OI + FIZ/YUR Positioning & Context Foundation

## Decision from R1.4.x
Price-only research is stopped. R1.4.8.1 produced no survivor after chronology robustness. Do not add more EMA/RSI/price-trigger variants to rescue the model.

## Objective
Test whether independent participant-behaviour information adds useful early regime/risk information beyond price alone.

Architecture:
PRICE STATE (control) + OI PARTICIPATION + FIZ/YUR POSITIONING + CONTEXT -> TRANSITION/RISK EVIDENCE

This release is a DATA/QUALITY foundation, not a trading strategy and not a production signal release.

## P0 Quality Gate
Every observation must carry event_time, available_time, decision_time, source, freshness/status and coverage. No forward fill across missing participant data. Missing or inaccessible data = N/A/BLOCKED_AUTH, never neutral and never fabricated.

## OI layer
Required features when valid intraday data exists:
- total OI and delta OI (absolute and percent)
- rolling percentile/extremeness computed only from information available at decision_time
- price/OI quadrant: price up/down x OI up/down
- persistence over completed observations

Thresholds such as +0.5% or P75 are hypotheses only until historical validation.

## Positioning layer
FUTOI semantics:
- FIZ = physical persons
- YUR = legal entities
- LegalNet = LegalLong - LegalShort
- RetailNet = RetailLong - RetailShort
- use changes and divergences, not the assumption that legal entities are smart money
- MOMENT is market/event time; SYSTIME is publication time and must control availability/no-lookahead.

Historical intraday FUTOI requires authenticated/subscribed MOEX access. Without credentials the historical positioning layer must report BLOCKED_AUTH. Public daily substitutes must not be mixed into the intraday model.

## Context layer
Context is independent from Crowd Score. Initial MOEX context candidates: IMOEX market state/breadth, RUB, OFZ yields/rate expectations, oil and material macro events. R1.5.0 only defines contracts and quality; it does not mechanically combine macro into Crowd Score.

## Validation question
Incremental value must be tested by ablation against a price-only control:
M0 PRICE CONTROL
M1 + OI
M2 + POSITIONING
M3 + OI + POSITIONING
M4 + CONTEXT (only when point-in-time quality is valid)

Primary metrics: transition lead time, false alarm rate, precision/recall for defined regime transitions, signal stability, and forward risk/return diagnostics. Do not call any score a crash probability.

## Release gate
PASS foundation only if source contracts, timestamps, freshness, missing-data behaviour and fail-closed semantics are tested. Historical alpha/regime GO is out of scope until sufficient authenticated history exists.

Production: NO-GO.
