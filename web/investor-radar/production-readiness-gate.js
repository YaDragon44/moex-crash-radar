// Investor Radar R1.8.36 — Production Readiness Re-Audit Gate
// Fail-closed release gate. Green unit tests alone are not enough for RC/production.
(function(global){
'use strict';
const REQUIRED=[
 'regression',
 'liveMoex',
 'browserSmoke',
 'sberValuation',
 'issuerRiskCoverage',
 'issuerRiskProvenance',
 'decisionIntegrity',
 'portfolioContextSafety',
 'security',
 'architectureSimplicity'
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
  passCount:REQUIRED.length-blockers.length,
  totalChecks:REQUIRED.length,
  completionPct:Math.round(((REQUIRED.length-blockers.length)/REQUIRED.length)*100),
  decision:ready?'RELEASE_CANDIDATE_ELIGIBLE':'DO_NOT_RELEASE',
  message:ready?'Production readiness gate passed.':'Недостаточно данных для обоснованного вывода',
  rule:'R1.8 may not be released while any blocking production-readiness check is missing, partial, failed, or unverified.'
 };
}
global.InvestorRadarProductionReadiness={REQUIRED,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarProductionReadiness;
})(typeof window!=='undefined'?window:globalThis);
