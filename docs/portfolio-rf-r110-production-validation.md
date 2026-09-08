# Portfolio RF R1.1 — Production Validation

Date: 2026-09-08
Status: PARTIAL / ACTION REQUIRED
Baseline: R1.0 Production, main commit c477bd5eef863f96fb83c89ddc113774a7961e2e

## Verified PASS

- Repository CI after R0.10.1: PASS.
- GitHub Pages workflow run 94: PASS.
- Real MOEX snapshot collection in deployment workflow: PASS.
- Dashboard contract validation in deployment workflow: PASS.
- Static site build: PASS.
- GitHub Pages deployment: PASS.
- Production page is static and first render does not depend on MOEX.
- Manual MOEX request has 8 second timeout, response-shape validation, duplicate request guard and fail-soft retention of prior valid prices.
- No backend, scheduler, polling, service worker, local storage or automatic trading added.

## Production-quality findings

### P1 — Release identity mismatch
Production HTML still identifies itself as `R0.10 · Production Hardening` and `<title>Портфель РФ · R0.10</title>` although R1.0 was accepted as the production baseline.

Impact: users cannot distinguish the accepted production baseline from the pre-acceptance hardening build.

Required fix: update visible release identity only after the validation findings are addressed.

### P1 — Price decision gate is not implemented
Every security has the Price field hard-coded as `?`. Live MOEX refresh only fills the separate MOEX market-price column. Therefore the chain `БИЗНЕС → ЦЕНА → РИСК → ДЕЙСТВИЕ` is incomplete: a displayed HOLD/WATCH action is not derived from a validated price/valuation gate.

Impact: the dashboard can look decision-ready while valuation evidence is absent.

Required fix: replace `?` with explicit `Н/Д` / `НЕДОСТАТОЧНО ДАННЫХ` and prevent any BUY/ADD action unless a valuation rule has verified evidence.

### P1 — Freshness/provenance is missing from fundamental states
Business and Risk traffic lights are embedded as static symbols without `as_of`, source or evidence reference in the UI.

Impact: a green/yellow state may become stale while still looking current.

Required fix: show freshness/evidence state or downgrade stale/unverified values to gray.

### P1 — Portfolio health summary regressed out of the production UI
R0.10 focuses on architecture/production cards. The user-required portfolio traffic-light summary and explanation are not present as a primary portfolio health block.

Required fix: restore one compact portfolio health card with status, reason and data sufficiency.

### P2 — Rebalancing policy is no longer visible
The model weights and acceptable ranges remain in the table, but the R0.8 explanation that ranges are model policy rather than fair-value targets is no longer visible.

Required fix: restore the disclaimer in compact form.

### P2 — No user-visible historical-validation state
The production UI says `Backtest: НЕ ЗАЯВЛЕН`, but does not communicate the R0.9 conclusion: insufficient point-in-time decision history for an unbiased historical performance conclusion.

Required fix: state this explicitly instead of a generic backtest label.

## Validation verdict

Technical production baseline: PASS.
Investment decision quality: PARTIAL.
Overall R1.1 Production Validation: YELLOW / ACTION REQUIRED.

Do not add new portfolio analytics until P1 findings are closed. Recommended next patch: R1.1.1 Decision Integrity Hotfix, limited to release identity, explicit missing-data states, evidence freshness, portfolio traffic light, and restoration of model-range disclaimer. No new engine or backend is required.
