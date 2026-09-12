// Investor Radar R1.8.46 — SBER Valuation Blocker Re-Audit
// Collapses the live valuation state into explicit remaining blockers. No recommendation is produced here.
(function(global){
'use strict';
function ok(x){return x?.verified===true&&x?.status==='VERIFIED';}
function audit(input={}){
 const blockers=[];
 if(!ok(input.peRuntime)) blockers.push('pe_runtime');
 if(!ok(input.pbRuntime)) blockers.push('pb_bank_valuation');
 if(!ok(input.bankQuality)) blockers.push('bank_quality');
 if(!ok(input.reportedBvps)) blockers.push('reported_common_bvps');
 const price=Number(input.currentPrice);
 if(!(Number.isFinite(price)&&price>0&&input.priceVerified===true)) blockers.push('current_price');
 const verified=blockers.length===0;
 return {
  ticker:'SBER',status:verified?'VERIFIED':'PARTIAL',verified,blockers,
  components:{pe:input.peRuntime?.status||'MISSING',pb:input.pbRuntime?.status||'MISSING',quality:input.bankQuality?.status||'MISSING',reportedBvps:input.reportedBvps?.status||'MISSING',price:!blockers.includes('current_price')?'VERIFIED':'LOCK'},
  peerCount:Array.isArray(input.peRuntime?.peers?.points)?input.peRuntime.peers.points.length:0,
  historicalPeCount:Array.isArray(input.peRuntime?.historical?.points)?input.peRuntime.historical.points.length:0,
  pb:ok(input.pbRuntime)?Number(input.pbRuntime.pb):null,
  currentPrice:!blockers.includes('current_price')?price:null,
  denominatorSource:ok(input.reportedBvps)?'SBER_ANNUAL_REPORT_2025_NET_ASSETS_PER_COMMON_SHARE':null,
  message:verified?'SBER valuation evidence blockers are cleared at runtime.':'Недостаточно данных для обоснованного вывода',
  rule:'R1.8 release still requires the separate production-readiness gate; this audit only evaluates SBER valuation evidence.'
 };
}
global.InvestorRadarSberValuationBlockerReaudit={audit};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberValuationBlockerReaudit;
})(typeof window!=='undefined'?window:globalThis);
