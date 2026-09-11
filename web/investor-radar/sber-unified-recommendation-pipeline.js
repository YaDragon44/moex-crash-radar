// Investor Radar R1.8.25 — SBER Unified Recommendation Pipeline
// DATA -> FACTS -> RISK -> VALUATION COMPLETENESS -> PORTFOLIO CONTEXT -> DECISION
// Fail-closed: unresolved bank valuation or missing portfolio context can only produce WATCH.
(function(global){
'use strict';
function build(input){
 const missing=[];
 const Rec=input?.recommendationEngine;
 const Complete=input?.completenessGate;
 const Quality=input?.bankQuality;
 const Bank=input?.bankValuation;
 const Equity=input?.equityAttribution;
 const pe=input?.peRuntime;
 if(!Rec?.decide) missing.push('recommendation_engine');
 if(!Complete?.assess) missing.push('completeness_gate');
 if(!pe) missing.push('pe_runtime');
 if(!Bank) missing.push('bank_valuation');
 if(!Quality) missing.push('bank_quality');
 if(!Equity) missing.push('equity_attribution');
 if(missing.length) return {ticker:'SBER',status:'LOCK',verified:false,missing,decision:null};

 const completeness=Complete.assess({
  peRuntime:pe,
  bankValuation:Bank,
  bankQuality:Quality,
  equityAttribution:Equity,
  valuationLabel:input?.valuationLabel
 });

 const decisionInput={
  ticker:'SBER',
  price:input?.price,
  fundamental:input?.fundamental,
  valuation:input?.valuation,
  valuationCompleteness:completeness,
  risk:input?.risk,
  portfolio:input?.portfolio,
  facts:Array.isArray(input?.facts)?input.facts:[],
  trigger:input?.trigger
 };
 const decision=Rec.decide(decisionInput);
 const verified=completeness.verified===true&&decision?.gate?.ok===true;
 return {
  ticker:'SBER',
  status:verified?'VERIFIED':'PARTIAL',
  verified,
  completeness,
  decision,
  missing:Array.from(new Set([...(completeness.missing||[]),...(decision?.gate?.missing||[])])),
  rule:'SBER active recommendation requires verified valuation completeness and explicit portfolio context. Incomplete evidence must resolve to НАБЛЮДАТЬ.'
 };
}
global.InvestorRadarSberUnifiedRecommendation={build};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberUnifiedRecommendation;
})(typeof window!=='undefined'?window:globalThis);
