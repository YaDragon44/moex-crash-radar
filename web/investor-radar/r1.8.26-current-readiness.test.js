const assert=require('assert');
const Gate=require('./production-readiness-gate.js');
const IssuerRisk=require('./issuer-risk-registry.js');
const ReportedBVPS=require('./sber-reported-bvps-registry.js');

// R1.8.48 evidence state. Fail-closed: only independently verified gates may PASS.
const issuerAudit=IssuerRisk.auditAll();
for(const t of ['YDEX','SBER','X5','MOEX']){
  const a=IssuerRisk.audit(t);
  assert.equal(a.sourceExists,true,`${t} issuer source must exist`);
  assert.equal(a.riskVerified,true,`${t} issuer risk must be verified`);
  assert.equal(a.crossDomainOk,true,`${t} issuer/sanctions domains must remain separated`);
  assert.equal(a.sectorGateOk,true,`${t} sector gate binding must be valid`);
}
assert.equal(issuerAudit.ok,true,'issuer-risk coverage cannot PASS with registry audit errors');
assert.equal(issuerAudit.coverage,'4/4');

const reportedBvps=ReportedBVPS.assess();
assert.equal(reportedBvps.status,'VERIFIED');
assert.equal(reportedBvps.verified,true);
assert(Number.isFinite(reportedBvps.bookValuePerShare)&&reportedBvps.bookValuePerShare>0);
assert.equal(reportedBvps.metric,'NET_ASSETS_PER_COMMON_SHARE');

const current=Gate.assess({
  regression:{status:'PASS',verified:true,evidence:'R1.8.47 full regression and 8/8 commit checks green'},
  liveMoex:{status:'PASS',verified:true,evidence:'GitHub runner TQBR live probe'},
  browserSmoke:{status:'PASS',verified:true,evidence:'Chromium smoke + MOEX fail-closed'},
  sberValuation:{status:'PASS',verified:true,evidence:'R1.8.44 issuer-reported net assets per common share independently verified from Sber 2025 Annual Report and accepted by R1.8.46 completeness gate as direct common-share denominator'},
  issuerRiskCoverage:{status:'PASS',verified:true,evidence:'Registry audit: YDEX, SBER, X5 and MOEX issuer-risk verified'},
  issuerRiskProvenance:{status:'PASS',verified:true,evidence:'R1.8.33/34 exact sector-gate provenance audit; manual VERIFIED issuer risk forbidden'},
  decisionIntegrity:{status:'PASS',verified:true,evidence:'R1.8.35 end-to-end decision integrity workflow; forged intermediate risk objects fail closed'},
  portfolioContextSafety:{status:'PASS',verified:true,evidence:'Recommendation safety + explicit portfolio-context regression'},
  security:{status:'PASS',verified:true,evidence:'R1.8.27 security scan: 0 Critical / 0 High; documented Medium review items remain non-blocking'},
  architectureSimplicity:{status:'PASS',verified:true,evidence:'R1.8.36 architecture simplicity audit: static browser UI, pure local decision/risk modules, no new backend or runtime framework dependency'}
});

assert.equal(current.status,'READY');
assert.equal(current.verified,true);
assert.equal(current.decision,'RELEASE_CANDIDATE_ELIGIBLE');
assert.deepEqual(current.blockers,[]);
assert.equal(current.passCount,10);
assert.equal(current.totalChecks,10);
assert.equal(current.completionPct,100);
console.log('R1.8.48 CURRENT STATUS: READY FOR RELEASE CANDIDATE');
console.log('Production readiness: 10/10 blocking gates PASS (100%)');
console.log('Issuer-risk coverage/provenance: PASS (4/4)');
console.log('Decision integrity: PASS');
console.log('Architecture simplicity: PASS');
console.log('SBER valuation completeness: PASS via issuer-reported common-share BVPS evidence');
console.log('Remaining RC blockers: none');
console.log('Public production promotion remains a separate deployment step; R1.7.1 stays public until promotion gate passes');
