// Investor Radar R1.8.22 — SBER Valuation Completeness Gate
// One fail-closed status for bank valuation. P/E alone must never upgrade SBER to a full valuation.
(function(global){
'use strict';
function ok(x){return x?.verified===true&&x?.status==='VERIFIED';}
function assess(input){
 const pe=input?.peRuntime;
 const bank=input?.bankValuation;
 const quality=input?.bankQuality;
 const equity=input?.equityAttribution;
 const missing=[];
 if(!ok(pe)) missing.push('pe_runtime');
 if(!ok(bank)) missing.push('pb_bank_valuation');
 if(!ok(quality)) missing.push('bank_quality');
 if(!ok(equity)) missing.push('common_equity_share_basis');
 const verified=missing.length===0;
 const qualityTraffic=quality?.traffic||bank?.traffic||'GRAY';
 return {
  ticker:'SBER',
  status:verified?'VERIFIED':'PARTIAL',
  verified,
  traffic:verified?qualityTraffic:'GRAY',
  valuationLabel:verified?(input?.valuationLabel||'VERIFIED_MODEL_OUTPUT'):'INSUFFICIENT_DATA',
  missing,
  components:{
   peRuntime:pe?.status||'MISSING',
   bankValuation:bank?.status||'MISSING',
   bankQuality:quality?.status||'MISSING',
   equityAttribution:equity?.status||'MISSING'
  },
  message:verified?'Full SBER valuation evidence gate passed.':'Недостаточно данных для обоснованного вывода',
  rule:'Full cheap/fair/expensive classification requires verified P/E runtime, P/B bank valuation, bank quality and common-equity/share basis. No component can be inferred from another.'
 };
}
global.InvestorRadarSberValuationCompleteness={assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberValuationCompleteness;
})(typeof window!=='undefined'?window:globalThis);
