const assert=require('assert');
const Gate=require('./production-readiness-gate.js');
const IssuerRisk=require('./issuer-risk-registry.js');

// R1.8.33 evidence state. Fail-closed: only independently verified gates may PASS.
const issuerAudit=IssuerRisk.auditAll();
for(const t of ['YDEX','SBER','X5','MOEX']){
  const a=IssuerRisk.audit(t);
  assert.equal(a.sourceExists,true,`${t} issuer source must exist`);
  assert.equal(a.riskVerified,true,`${t} issuer risk must be verified`);
  assert.equal(a.crossDomainOk,true,`${t} issuer/sanctions domains must remain separated`);
  assert.equal(a.sectorGateOk,true,`${t} sector gate binding must be valid`);
}
assert.equal(issuerAudit.ok,true,'issuer-risk coverage cannot PASS with registry audit errors');

const current=Gate.assess({
  regression:{status:'PASS',verified:true,evidence:'R1.8 regression suite'},
  liveMoex:{status:'PASS',verified:true,evidence:'GitHub runner TQBR live probe'},
  browserSmoke:{status:'PASS',verified:true,evidence:'Chromium smoke + MOEX fail-closed'},
  sberValuation:{status:'PARTIAL',verified:false,evidence:'Common-equity/share basis and P/B remain unresolved'},
  issuerRiskCoverage:{status:'PASS',verified:true,evidence:'R1.8.32 registry audit: YDEX, SBER, X5 and MOEX issuer-risk verified with cross-domain semantics clean'},
  portfolioContextSafety:{status:'PASS',verified:true,evidence:'Recommendation safety + explicit portfolio-context regression'},
  security:{status:'PASS',verified:true,evidence:'R1.8.27 security scan: 0 Critical / 0 High; 3 Medium HTML-sink review items'}
});

assert.equal(current.status,'HOLD');
assert.equal(current.verified,false);
assert.equal(current.decision,'DO_NOT_RELEASE');
assert.deepEqual(current.blockers,['sberValuation']);
assert(!current.blockers.includes('issuerRiskCoverage'));
assert(!current.blockers.includes('security'));
assert(!current.blockers.includes('regression'));
assert(!current.blockers.includes('liveMoex'));
assert(!current.blockers.includes('browserSmoke'));
assert(!current.blockers.includes('portfolioContextSafety'));
console.log('R1.8.33 CURRENT STATUS: HOLD');
console.log('Issuer-risk coverage: PASS (4/4)');
console.log('Remaining blocker:', current.blockers.join(', '));
