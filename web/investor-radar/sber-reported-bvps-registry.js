// Investor Radar R1.8.44 — SBER Issuer-Reported Common BVPS Evidence
// Primary evidence extracted from Sber 2025 Annual Report. Uses the issuer's own
// per-common-share net-assets metric instead of reconstructing common equity from total capital.
(function(global){
'use strict';

const EVIDENCE=Object.freeze({
 ticker:'SBER',
 period:'2025',
 metric:'NET_ASSETS_PER_COMMON_SHARE',
 valueRub:390.02,
 previous:{2023:307.68,2024:335.21},
 source:'Sberbank Annual Report 2025',
 sourceUrl:'https://www.sberbank.com/common/img/uploaded/_new_site/com/gosa2026/sber-ar-2025-ru.pdf',
 documentSha256:'4550c786daa88e7e9de0ab5bbb650c27273b3e9d12fa67693d5768702358a6cd',
 locator:'page:132:line:49',
 extractedContext:'Чистые активы на обыкновенную акцию: 2023 — 307.68; 2024 — 335.21; 2025 — 390.02 RUB',
 primary:true,
 extracted:true,
 semantic:'Issuer-reported net assets per ordinary/common share; accepted as the direct common-share book-value denominator for P/B, without reallocating total equity between common and preferred shares.',
 supportingEquity:{
  metric:'EQUITY_ATTRIBUTABLE_TO_BANK_SHAREHOLDERS',
  valueRubBn2025:8351.6,
  sourceLocator:'page:142:line:24',
  note:'Supporting total shareholder-equity evidence only; not independently treated as attributable common equity.'
 },
 asOf:'2025-12-31'
});

function assess(input=EVIDENCE){
 const missing=[];
 if(input?.primary!==true) missing.push('primary_source');
 if(input?.extracted!==true) missing.push('extracted_field');
 if(!(Number.isFinite(Number(input?.valueRub))&&Number(input.valueRub)>0)) missing.push('positive_bvps');
 if(!input?.sourceUrl||!input?.documentSha256||!input?.locator||!input?.asOf) missing.push('traceability');
 if(input?.metric!=='NET_ASSETS_PER_COMMON_SHARE') missing.push('common_share_semantics');
 const verified=missing.length===0;
 return {
  ticker:'SBER',status:verified?'VERIFIED':'PARTIAL',verified,missing,
  bookValuePerShare:verified?Number(input.valueRub):null,
  metric:input?.metric||null,source:verified?input.source:null,sourceUrl:verified?input.sourceUrl:null,
  documentSha256:verified?input.documentSha256:null,locator:verified?input.locator:null,asOf:verified?input.asOf:null,
  supportingEquity:verified?input.supportingEquity:null,
  rule:'Use issuer-reported net assets per common share directly for P/B. Do not reconstruct common BVPS from MOEX total capital or regulatory capital.'
 };
}

global.InvestorRadarSberReportedBVPS={EVIDENCE,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberReportedBVPS;
})(typeof window!=='undefined'?window:globalThis);
