# IR-C2 Evidence — X5 Historical Price / Share-Basis Continuity

Date: 2026-09-24  
Status: OBJECTIVE LIMITATION / INSUFFICIENT

## Question

Why does X5 have verified EPS for 2023–2025 but only one usable historical P/E observation?

## Evidence

1. The current security is ordinary share `X5`, ISIN `RU000A108X38`, issuer PJSC X5 Corporate Center.
2. Moscow Exchange states that trading in these ordinary shares started on **2025-01-09**.
3. Before that, the exchange-traded X5 instrument was `FIVE`: Global Depositary Receipts of X5 Retail Group N.V., ISIN `US98387E2054`.
4. MOEX suspended FIVE trading from 2024-04-05 and later terminated/delisted it from 2024-11-25.
5. X5's share-distribution materials describe the legal process by which holders/ultimate owners of X5 Retail Group N.V. DRs could receive direct shares in the Russian X5 Corporate Centre under Federal Law 470-FZ.

Primary sources:
- MOEX, start of X5 ordinary-share trading: https://www.moex.com/n76387
- MOEX, X5 security page: https://www.moex.com/ru/stocks/X5
- MOEX, suspension of FIVE: https://www.moex.com/n68669
- MOEX, termination/delisting of FIVE: https://www.moex.com/n74205
- X5, share distribution: https://www.x5.ru/en/investors/share-distribution/

## Conclusion

The current `X5` ordinary share did not trade on MOEX in 2023 or 2024. Therefore the absence of X5 year-end candles for those years is not a runtime defect.

The earlier `FIVE` observations are prices of a different security type and legal instrument (GDR of X5 Retail Group N.V.). They MUST NOT be silently substituted for current X5 ordinary-share prices in the existing Historical P/E factory.

Current baseline result:
- 2023 EPS: verified, but no comparable current-X5 share price;
- 2024 EPS: verified, but no comparable current-X5 share price;
- 2025 EPS + X5 year-end share price: one usable observation;
- Historical P/E gate: **INSUFFICIENT (1/3)**.

## Completion decision

IR-C2 is CLOSED as an **objective data/instrument-continuity limitation**, not as an implementation failure.

No synthetic backfill, GDR substitution, conversion factor, or alternative valuation methodology is authorized by the current baseline.
