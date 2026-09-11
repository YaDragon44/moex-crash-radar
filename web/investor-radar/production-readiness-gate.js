// Investor Radar R1.8.26 — Production Readiness Gate
// Fail-closed release gate. A green test suite alone is not enough for production release.
(function(global){
'use strict';
const REQUIRED=[
 'regression',
 'liveMoex',
 'browserSmoke',
 'sberValuation',
 'issuerRiskCoverage',
 'portfolioContextSafety',
 'security'
];
function pass(x){return x?.status==='PASS'&&x?.verified===true;}
function assess(input={}){
 const checks={};
 for(const k of REQUIRED){
  const x=input[k]||{};
  checks[k]={status:x.status||'MISSING',verified:x.verified===true,evidence:x.evidence||null};
 }
 const blockers=REQUIRED.filter(k=>!pass(checks[k]));
 const ready=blockers.length===0;
 return {
  release:'R1.8',
  status:ready?'READY':'HOLD',
  verified:ready,
  blockers,
  checks,
  decision:ready?'RELEASE_CANDIDATE_ELIGIBLE':'DO_NOT_RELEASE',
  message:ready?'Production readiness gate passed.':'Недостаточно данных для обоснованного вывода',
  rule:'R1.8 may not be released while any blocking production-readiness check is missing, partial, failed, or unverified.'
 };
}
global.InvestorRadarProductionReadiness={REQUIRED,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarProductionReadiness;
})(typeof window!=='undefined'?window:globalThis);
