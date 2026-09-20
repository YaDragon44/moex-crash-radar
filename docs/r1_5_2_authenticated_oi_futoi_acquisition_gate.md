# R1.5.2 — Authenticated OI/FUTOI Acquisition Gate

## Objective
Prepare and validate the authenticated MOEX acquisition path required to unlock historical point-in-time OI and FIZ/YUR positioning research.

This release does not require credentials to exist in CI and must never store credentials in the repository. Without valid runtime credentials/subscription, the adapter must fail closed with BLOCKED_AUTH.

## Required authenticated sources
1. Historical/intraday open-interest source with point-in-time timestamps suitable for MX/SI/SR/GZ.
2. MOEX analytical FUTOI product for FIZ/YUR positioning where subscribed.

## Timestamp contract
Every row must preserve:
- source
- security/contract id
- event_time
- available_time
- decision_time
- quality

For FUTOI, MOMENT is market/event time and SYSTIME is publication/availability time. A row is usable only when available_time <= decision_time. No look-ahead.

## Authentication contract
Credentials/tokens/cookies are runtime-only secrets. Never commit them, print them, save them in artifacts, or expose them in logs. Adapters must support an explicit unauthenticated mode returning BLOCKED_AUTH.

## Coverage gate
Authenticated history is DATA_READY only if:
- >=2 pilot families have usable history;
- >=2 chronological subperiods are covered;
- timestamps and publication semantics are valid;
- missing periods are explicit and not forward-filled;
- source contracts are stable across sampled rows.

## Research unlock
M1 Price+OI may run only after OI DATA_READY.
M2 Price+Positioning and M3 Price+OI+Positioning may run only after FUTOI DATA_READY.
Until then all remain locked.

Production: NO-GO.
