# Investor Radar — Completion Requirements v1.0

Status: ACTIVE BASELINE  
Scope: `web/investor-radar` in `YaDragon44/moex-crash-radar`  
Date: 2026-09-23

## 1. Goal

Complete and harden the existing seven-ticker Investor Radar without inventing data, weakening verification gates, creating duplicate engines, or expanding product scope.

Universe: SBER, YDEX, X5, MOEX, VKCO, AFLT, GAZP.

Primary principle: FACT → ANALYSIS → DECISION. Missing or non-comparable evidence must remain LOCK / INSUFFICIENT / LIMITED / N/A rather than being converted into a positive result.

## 2. Required product surface

The production view MUST:
- show all seven tickers;
- use the comparison matrix as the primary view;
- show live current MOEX price;
- show Fundamental, EPS, Historical P/E, Peer P/E, Issuer Risk, Sanctions, Full Risk, Recommendation / итог;
- distinguish PASS, INSUFFICIENT, LIMITED, LOCK and N/A truthfully;
- include a per-ticker «ИТОГ АНАЛИЗА»;
- fail closed when a mandatory decision input is missing.

No daily percentage-change requirement is authorized in this baseline.

## 3. Data and provenance

Current price MUST come from live MOEX ISS.

Fundamental/EPS data MUST have explicit metric, source and asOf metadata. A value MUST NOT become verified merely because it is present.

Historical P/E MUST use comparable positive EPS and a price observation on the same share basis. VERIFIED requires at least 3 valid observations.

Peer P/E MUST use an approved peer universe, positive comparable verified EPS, verified current/reference price and compatible corporate-action basis. VERIFIED requires at least 2 usable peers.

Negative EPS MUST NOT be forced into P/E. Where P/E is economically inapplicable, UI SHOULD show N/A.

Sanctions/regulatory status MUST be entity-specific and source-backed. Absence of a search match MUST NOT be treated as proof of no sanctions. Status of a subsidiary/affiliate MUST NOT automatically be transferred to the issuer.

Issuer risk MUST preserve sector-gate provenance.

Portfolio-aware actions MUST require explicit portfolio context. Unknown holdings MUST NOT be represented as `held:false`.

## 4. Valuation gate

Existing valuation methodology remains:
- verified positive EPS;
- >=3 historical P/E observations;
- >=2 peer P/E observations;
- explicit source/asOf;
- anchor P/E = 60% historical median + 40% peer median;
- fair-value band = ±15%.

These thresholds MUST NOT be weakened merely to obtain a VERIFIED result.

## 5. Risk gate

Full Risk requires verified:
- market history;
- liquidity;
- issuer risk + provenance;
- sanctions/regulatory status.

Existing market/liquidity scoring remains 70% market + 30% liquidity. Sanctions designation/materiality does not automatically imply thesisBroken or SELL.

## 6. Recommendation gate

Active actions (BUY/ADD/HOLD/NO_ADD/REDUCE/SELL) require all mandatory decision inputs, including explicit portfolio context.

When critical inputs are missing, the product MUST remain WAIT / НАБЛЮДАТЬ and state the blockers.

## 7. Mandatory completion work

### IR-C1 — Peer price runtime defect
Resolve why verified peers VTBR, T and LENT are still reported as `verified_price_missing` in production. Inspect the actual MOEX ISS payload/board behavior; do not assume TQBR is sufficient. Add regression evidence proving usable peer prices when available.

Acceptance:
- source/asOf preserved;
- no fabricated/fallback hardcoded prices;
- SBER peer factory produces 2 usable peers if MOEX actually exposes valid prices;
- X5 LENT price becomes usable if MOEX actually exposes a valid price;
- production smoke asserts the resolved behavior or an explicit truthful blocker.

### IR-C2 — X5 historical continuity
Determine why X5 has 3 verified EPS periods but only 1 historical P/E observation. Verify instrument/share-basis continuity around redomiciliation/current PJSC share basis.

Acceptance:
- either >=3 genuinely comparable observations and VERIFIED historical P/E;
- or documented INSUFFICIENT with the exact non-comparable/missing years and reason.
Legacy GDR prices MUST NOT be silently mixed with current-share EPS.

### IR-C3 — YDEX/X5 sanctions evidence
Perform reproducible entity-specific verification against authoritative current sanctions sources, including ownership/control implications where applicable.

Acceptance:
- PASS/verified only with sufficient evidence;
- otherwise remain LOCK/UNKNOWN with documented reason;
- Yandex Bank status MUST NOT be transferred to MKPAO Yandex without legal-entity/ownership evidence.

### IR-C4 — Portfolio context
Provide a real read-only portfolio source or an explicitly authorized portfolio-input mechanism before personalized active actions are enabled.

Acceptance:
- `portfolio.held` is explicitly known;
- no inference from memory or generic production assumptions;
- recommendation engine remains fail-closed when context is absent.

### IR-C5 — Final completeness review
After C1–C4, run a final seven-ticker matrix audit:
`REQUIREMENT → IMPLEMENTED → EVIDENCE → REMAINING GAP → MANDATORY / OBJECTIVE LIMITATION / NOT AUTHORIZED`.

## 8. Accepted objective limitations

The following are not defects by themselves:
- VKCO P/E = N/A while EPS is negative;
- MOEX Peer P/E = LIMITED until a defensible comparable universe is approved;
- AFLT Peer P/E = LIMITED without >=2 comparable public airline peers;
- GAZP Peer P/E = LIMITED without an approved integrated-gas peer universe;
- YDEX historical P/E = INSUFFICIENT while only two comparable current-issuer annual periods exist;
- AFLT/GAZP historical P/E = INSUFFICIENT while fewer than 3 positive comparable observations exist.

Do not invent peers, history or alternative data merely to clear these states.

## 9. Not authorized

Without a separate owner decision, do NOT:
- create a new valuation/risk/recommendation engine;
- add a database or new platform/service;
- expand the ticker universe;
- weaken verification thresholds;
- fabricate historical prices, EPS, sanctions status or portfolio holdings;
- introduce an alternative valuation methodology solely to eliminate N/A/LIMITED states;
- treat objective data limitations as implementation failures.

## 10. Current completion snapshot

Production capability:
- UI / seven-ticker matrix: DONE
- live MOEX prices: DONE
- issuer risk provenance: DONE
- risk engine: DONE
- recommendation engine: DONE
- production CI/browser smoke: DONE
- Historical P/E: PARTIAL
- Peer P/E: PARTIAL
- sanctions completeness: PARTIAL
- portfolio input mechanism: DONE; context remains explicit/unknown until the user selects held/not-held
- verified full valuation: PARTIAL by evidence availability; SBER VERIFIED
- completion sequence IR-C1…IR-C5: CLOSED

Final baseline result: no remaining mandatory implementation defect. See `FINAL_COMPLETENESS_REVIEW.md`.


## 11. Owner-authorized Investor / Trader separation — 2026-09-24

The product MUST expose two independent decisions per ticker.

### INVESTOR
Purpose: months/years capital-allocation decision.
- Uses verified fundamentals, valuation, issuer/full risk and sanctions/regulatory evidence.
- Uses the already established owner portfolio context; production UI MUST NOT ask the owner to re-enter per-ticker holdings.
- Actions: BUY / ADD / HOLD / NO_ADD / REDUCE / SELL / WATCH.
- Current owner context for the seven-ticker scope is fixed from prior explicit input: held SBER/YDEX/X5/VKCO/AFLT; not held MOEX/GAZP. Changes require a new explicit owner update, not UI inference.
- Existing fail-closed valuation/risk/recommendation gates remain unchanged.

### TRADER
Purpose: short-/medium-term buy/sell setup.
- MUST NOT be blocked or altered by `portfolio_context`.
- Uses live MOEX ISS OHLCV: D1 and H1; H4 is derived deterministically from H1.
- Uses IMOEX D1 as market context.
- Output: LONG / SHORT / WAIT / NO_TRADE; Observation/Entry zone; Trigger; Stop/Invalidation; TP1/TP2/TP3; R/R; Confluence Score /19; READY/WAIT/INVALID where applicable.
- Current minimal confluence implementation may score only evidence actually calculated. Wyckoff/Elliott MUST score zero unless separately evidenced; they MUST NOT be inferred merely to raise the score.
- READY requires an executed H1 trigger, Confluence >=13/19 and R/R >=2.
- Missing D1/H1/IMOEX/ATR data MUST fail closed.
- PASS continues to mean evidence/data gate quality; READY means an executable trading setup.

This authorization permits the thin `trader-decision.js` layer inside the existing Investor Radar UI. It does not authorize a new platform, service, database, ticker universe or weaker investment gates.
