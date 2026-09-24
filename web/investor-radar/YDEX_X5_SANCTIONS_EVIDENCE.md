# IR-C3 Evidence — YDEX / X5 Sanctions & Regulatory Verification

Date: 2026-09-24

## YDEX — VERIFIED MATERIAL GROUP EXPOSURE / ISSUER NOT DESIGNATED BY TRANSFER

Entity under analysis: MKPAO Yandex (MOEX: YDEX).

Primary evidence:
- EU Council Decision (CFSP) 2025/1495 adds **Yandex Bank** to the transaction-ban list, effective 2025-08-09.
- UK Sanctions List identifies **JOINT STOCK COMPANY "YANDEX BANK"**, reference **RUS3621**, designated 2026-06-16.
- Yandex issuer disclosure dated 2025-07-19 states that the EU restrictions on Yandex Bank do not extend to head company MKPAO Yandex or other group subsidiaries.

Sources:
- https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202501495
- https://search-uk-sanctions-list.service.gov.uk/
- https://yandex.ru/company/news/19-07-2025-01

Decision:
- `verified=true`
- `material=true`
- `designated=false` for the YDEX issuer itself
- `level=HIGH`
- `status=SUBSIDIARY_RESTRICTED`

This does not mean “sanctions-free”. It records verified material group exposure while preventing the subsidiary's designation from being copied to the parent issuer.

## X5 — LOCK / UNKNOWN

Entity under analysis: PJSC X5 Corporate Center (MOEX: X5).

Primary evidence:
- Current X5 ordinary shares are shares of PJSC X5 Corporate Center, ISIN RU000A108X38.
- X5's share-distribution disclosure documents the 2024 transition from X5 Retail Group N.V. DR ownership to direct ownership in the Russian X5 entity.
- EU restrictive-measures materials concerning sanctioned Alfa Group shareholders contain references to historical **X5 Retail Group** in the statements of reasons for those individuals.
- Those references are not, by themselves, a designation of current PJSC X5 Corporate Center and do not establish current ownership/control attribution after the 2024 restructuring.

Sources:
- https://www.x5.ru/en/investors/shares/
- https://www.x5.ru/en/investors/share-distribution/
- https://eur-lex.europa.eu/eli/reg_impl/2025/1894/oj/eng

Decision:
- `verified=false`
- `material=null`
- `designated=null`
- `level=UNKNOWN`
- `status=LOCK`

Reason: available primary evidence does not establish a complete current ownership/control sanctions conclusion. A missing direct-list match is not treated as proof of clean status.

## IR-C3 completion

IR-C3 is CLOSED:
- YDEX: verified material group sanctions exposure, without false parent designation.
- X5: truthful LOCK/UNKNOWN due unresolved current ownership/control attribution.
