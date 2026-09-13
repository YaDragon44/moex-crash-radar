// Investor Radar R1.8.46 — SBER Valuation Completeness Gate
// One fail-closed status for bank valuation. P/E alone must never upgrade SBER to a full valuation.
// The common-share denominator may be satisfied either by a verified reconstructed equity/share basis
// OR by an issuer-reported common-share BVPS metric that is independently verified from the annual report.
(function(global){
'use strict';
function ok(x){return x?.verified===true&&x?.status==='VERIFIED';}
function assess(input){
 const pe=input?.peRuntime;
 const bank=input?.bankValuation;
 const quality=input?.bankQuality;
 const equity=input?.equityAttribution;
 const reportedBvps=input?.reportedBvps;
 const denominatorOk=ok(equity)||ok(reportedBvps);
 const denominatorSource=ok(reportedBvps)?'ISSUER_REPORTED_COMMON_BVPS':ok(equity)?'RECONSTRUCTED_COMMON_EQUITY_SHARE_BASIS':'MISSING';
 const missing=[];
 if(!ok(pe)) missing.push('pe_runtime');
 if(!ok(bank)) missing.push('pb_bank_valuation');
 if(!ok(quality)) missing.push('bank_quality');
 if(!denominatorOk) missing.push('common_equity_share_basis_or_reported_bvps');
 const verified=missing.length===0;
 const qualityTraffic=quality?.traffic||bank?.traffic||'GRAY';
 return {
  ticker:'SBER',
  status:verified?'VERIFIED':'PARTIAL',
  verified,
  traffic:verified?qualityTraffic:'GRAY',
  valuationLabel:verified?(input?.valuationLabel||'VERIFIED_MODEL_OUTPUT'):'INSUFFICIENT_DATA',
  missing,
  denominatorSource,
  components:{
   peRuntime:pe?.status||'MISSING',
   bankValuation:bank?.status||'MISSING',
   bankQuality:quality?.status||'MISSING',
   equityAttribution:equity?.status||'MISSING',
   reportedBvps:reportedBvps?.status||'MISSING'
  },
  message:verified?'Full SBER valuation evidence gate passed.':'Недостаточно данных для обоснованного вывода',
  rule:'Full cheap/fair/expensive classification requires verified P/E runtime, P/B bank valuation, bank quality, and an independently verified common-share denominator. Issuer-reported common BVPS is accepted directly; total capital is not.'
 };
}
global.InvestorRadarSberValuationCompleteness={assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberValuationCompleteness;
})(typeof window!=='undefined'?window:globalThis);
