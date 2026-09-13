// Investor Radar R1.8.46 — SBER Final Valuation Pipeline
// Fail-closed orchestration: market price -> P/E -> P/B -> bank quality -> denominator evidence -> completeness -> recommendation eligibility.
(function(global){
'use strict';
function statusOf(x){return x?.status||'MISSING';}
function build(input={}){
 const completeness=input.completenessGate;
 if(!completeness?.assess) return {ticker:'SBER',status:'LOCK',verified:false,traffic:'GRAY',action:'НАБЛЮДАТЬ',confidence:'НИЗКАЯ',reason:'missing_completeness_gate',message:'Недостаточно данных для обоснованного вывода'};
 const c=completeness.assess({
  peRuntime:input.peRuntime,
  bankValuation:input.bankValuation,
  bankQuality:input.bankQuality,
  equityAttribution:input.equityAttribution,
  reportedBvps:input.reportedBvps,
  valuationLabel:input.valuationLabel
 });
 const price=Number(input.price);
 const priceVerified=Number.isFinite(price)&&price>0&&input.priceVerified===true;
 const blockers=[...(c.missing||[])];
 if(!priceVerified) blockers.push('current_price');
 const verified=c.verified===true&&priceVerified;
 const traffic=verified?(c.traffic||'YELLOW'):'GRAY';
 return {
  ticker:'SBER',
  status:verified?'VERIFIED':'PARTIAL',
  verified,
  traffic,
  action:verified?(input.action||'НАБЛЮДАТЬ'):'НАБЛЮДАТЬ',
  confidence:verified?(input.confidence||'СРЕДНЯЯ'):'НИЗКАЯ',
  currentPrice:priceVerified?price:null,
  valuation:verified?c.valuationLabel:'INSUFFICIENT_DATA',
  recommendationEligible:verified,
  blockers:[...new Set(blockers)],
  denominatorSource:c.denominatorSource||'MISSING',
  components:{price:priceVerified?'VERIFIED':'LOCK',pe:statusOf(input.peRuntime),pb:statusOf(input.bankValuation),quality:statusOf(input.bankQuality),equityBasis:statusOf(input.equityAttribution),reportedBvps:statusOf(input.reportedBvps)},
  message:verified?'SBER final valuation pipeline passed all evidence gates.':'Недостаточно данных для обоснованного вывода',
  rule:'No active SBER valuation recommendation unless current price, P/E, P/B, bank quality and an independently verified common-share denominator are VERIFIED.'
 };
}
global.InvestorRadarSberFinalValuationPipeline={build};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberFinalValuationPipeline;
})(typeof window!=='undefined'?window:globalThis);
