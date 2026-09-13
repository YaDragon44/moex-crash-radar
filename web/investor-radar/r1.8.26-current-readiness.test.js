const assert=require('assert');
const Gate=require('./production-readiness-gate.js');
const IssuerRisk=require('./issuer-risk-registry.js');
const Preferred=require('./sber-preferred-treatment-evidence.js');

// R1.8.36 evidence state. Fail-closed: only independently verified gates may PASS.
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
const preferred=Preferred.assess();
assert.equal(preferred.status,'PARTIAL');
assert.equal(preferred.dividendEqualityVerified,true);
assert.equal(preferred.preferredTreatmentVerified,false);

const current=Gate.assess({
  regression:{status:'PASS',verified:true,evidence:'R1.8 regression suite'},
  liveMoex:{status:'PASS',verified:true,evidence:'GitHub runner TQBR live probe'},
  browserSmoke:{status:'PASS',verified:true,evidence:'Chromium smoke + MOEX fail-closed'},
  sberValuation:{status:'PARTIAL',verified:false,evidence:'Treasury/outstanding common-share basis is verified from CBR 0409810; SBERP security terms and 2025 dividend parity are verified. Current preferred liquidation/equity priority, defensible equity-allocation method and attributable common equity remain unresolved, so common BVPS/P-B stays blocked.'},
  issuerRiskCoverage:{status:'PASS',verified:true,evidence:'Registry audit: YDEX, SBER, X5 and MOEX issuer-risk verified'},
  issuerRiskProvenance:{status:'PASS',verified:true,evidence:'R1.8.33/34 exact sector-gate provenance audit; manual VERIFIED issuer risk forbidden'},
  decisionIntegrity:{status:'PASS',verified:true,evidence:'R1.8.35 end-to-end decision integrity workflow; forged intermediate risk objects fail closed'},
  portfolioContextSafety:{status:'PASS',verified:true,evidence:'Recommendation safety + explicit portfolio-context regression'},
  security:{status:'PASS',verified:true,evidence:'R1.8.27 security scan: 0 Critical / 0 High; documented Medium review items remain'},
  architectureSimplicity:{status:'PASS',verified:true,evidence:'R1.8.36 architecture simplicity audit: static browser UI, pure local decision/risk modules, no new backend or runtime framework dependency'}
});

assert.equal(current.status,'HOLD');
assert.equal(current.verified,false);
assert.equal(current.decision,'DO_NOT_RELEASE');
assert.deepEqual(current.blockers,['sberValuation']);
assert.equal(current.passCount,9);
assert.equal(current.totalChecks,10);
assert.equal(current.completionPct,90);
console.log('R1.8.36 CURRENT STATUS: HOLD');
console.log('Production readiness: 9/10 blocking gates PASS (90%)');
console.log('Issuer-risk coverage/provenance: PASS (4/4)');
console.log('Decision integrity: PASS');
console.log('Architecture simplicity: PASS');
console.log('Only blocker: SBER valuation completeness');
console.log('Remaining evidence: attributable common equity + current preferred liquidation/equity priority + defensible allocation method');
