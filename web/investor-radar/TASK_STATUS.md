# Investor Radar — Task Status

Date: 2026-09-24  
Requirements: `web/investor-radar/REQUIREMENTS.md`

## Overall

PRODUCT: LIVE  
ENGINE: READY  
7-TICKER COVERAGE: LIVE  
INFRASTRUCTURE: GREEN  
DATA COMPLETENESS: PARTIAL  
PORTFOLIO CONTEXT: UNKNOWN IN PUBLIC UI / PERSONAL ACTIONS LOCKED  
INVESTOR DECISION READINESS: PARTIAL / WAIT
TRADER DECISION LAYER: R1.9.0 LIVE / CLOSED
PORTFOLIO UI CLEANUP: R1.9.2 LIVE / CLOSED  
CAPITAL ALLOCATION: R2.0 LIVE / CLOSED

## Completed

- Seven-ticker production matrix.
- Live MOEX price column.
- Fundamental/EPS provenance gates.
- Historical P/E factory.
- Peer universe + peer EPS + peer P/E factory.
- Issuer-risk sector provenance for all seven tickers.
- Sanctions/regulatory fail-closed registry.
- Full Risk engine.
- Recommendation engine and per-ticker «ИТОГ АНАЛИЗА».
- Production CI and browser smoke.
- X5 audited 2023–2025 attributable earnings/EPS.
- MOEX FY2025 fundamentals/EPS.
- GAZP FY2024 attributable earnings/EPS.
- YDEX current-issuer IFRS series kept to two comparable periods rather than fabricating a third.
- False generic `portfolio.held=false` assumption removed.

## Active mandatory tasks

### IR-C1 — Peer price runtime defect — DONE
Explicit TQBR endpoint closed the runtime defect. Production smoke confirms SBER peer P/E VERIFIED with 2 usable peers (VTBR, T); X5 receives 1 usable peer (LENT), while MGNT remains correctly excluded for negative EPS. No hardcoded prices or weakened gates.

### IR-C2 — X5 historical continuity — DONE / OBJECTIVE LIMITATION
Primary MOEX/X5 evidence confirms current ordinary share X5 (ISIN RU000A108X38) began trading on 2025-01-09. 2023–2024 exchange history belongs to FIVE GDR (ISIN US98387E2054), a different security/legal instrument. It is not silently substituted into current-share Historical P/E. Result: X5 Historical P/E remains truthfully INSUFFICIENT (1/3). Evidence: `X5_HISTORICAL_CONTINUITY_EVIDENCE.md`.

### IR-C3 — YDEX/X5 sanctions evidence — DONE
YDEX now has verified material group exposure: EU transaction restrictions and UK RUS3621 apply to Yandex Bank, while the issuer itself is not falsely marked designated. YDEX Full Risk now passes. X5 remains truthfully LOCK/UNKNOWN because current ownership/control attribution is not sufficiently established after restructuring. Evidence: `YDEX_X5_SANCTIONS_EVIDENCE.md`.

### IR-C4 — Portfolio context — REPLACED BY R1.9.2 PUBLIC-UI BOUNDARY
Public Investor Radar has no portfolio controls, localStorage or embedded owner holdings. Unknown context remains fail-closed for BUY/ADD/HOLD/NO_ADD/REDUCE/SELL, while objective evidence PASS remains visible as neutral WATCH. Personal context belongs only to a separate personalized portfolio-management layer.

### IR-C5 — Final completeness review — DONE
Final baseline review completed in `FINAL_COMPLETENESS_REVIEW.md`. No remaining mandatory implementation defect was identified; remaining red/yellow states are documented data/methodology limitations or require future fresh evidence.

## R1.9.0 — Investor / Trader separation

- Investor decision remains portfolio-aware and uses the existing verified fundamental/valuation/risk gates.
- Trader decision is portfolio-independent and consumes MOEX D1/H1 OHLCV plus IMOEX D1; H4 is derived from H1.
- Trader outputs LONG/SHORT/WAIT/NO_TRADE with Entry, Trigger, Stop/Invalidation, TP1/TP2/TP3, R/R and Confluence /19.
- READY is fail-closed: H1 trigger + Score >=13/19 + R/R >=2.
- Wyckoff/Elliott are not inferred by the minimal layer and contribute 0 unless separately evidenced.
- Production validation CLOSED: CI PASS; Deploy Dashboard + public health PASS; post-deploy browser smoke PASS. Production snapshot: quotes 7/7, trader runtime 7/7, READY 0/7 at validation time.

## R1.9.2 — Remove Visible Portfolio Context UI

- Removed residual hardcoded portfolio state from the public page.
- Removed unused portfolio CSS and all portfolio-input semantics from the public UI.
- Investor objective PASS is now distinct from personal-action authorization: unknown holding produces neutral WATCH with `PERSONAL ACTIONS LOCKED`, never inferred `held=false`.
- Trader remains independent of portfolio context.

## Current objective limitations

- VKCO P/E: N/A while EPS < 0.
- MOEX peer universe: LIMITED.
- AFLT peer universe: LIMITED; historical positive observations <3.
- GAZP peer universe: LIMITED; historical positive observations <3.
- YDEX comparable annual history: 2 periods.
- X5 has only one positive usable peer EPS (LENT) in the approved MGNT/LENT universe; MGNT EPS is negative.

## Next task

**NONE — R2.0 is deployed and validated.**

Do not open new feature scope without a new owner decision. Preserve fail-closed gates and refresh source evidence when it becomes stale.


## R2.0 — Capital Allocation & Portfolio Fit

- Thin policy layer over existing verified Investor, valuation, risk and Trader outputs.
- New Capital is user-entered; no amount is hardcoded as a recommendation.
- Deployment is allowed only for verified attractive opportunity + Trader READY; otherwise capital is truthfully reserved or not allocated.
- Portfolio Fit is UNKNOWN / INSUFFICIENT in the public view without inventing holdings or concentration.
- Production validation CLOSED: CI PASS; Deploy Dashboard + Public Health PASS; post-deploy browser smoke PASS.
