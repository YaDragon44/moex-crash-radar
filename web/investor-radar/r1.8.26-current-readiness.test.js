const assert=require('assert');
const Gate=require('./production-readiness-gate.js');

// Evidence state after R1.8.25. This is deliberately fail-closed.
// PASS values below are backed by CI/browser/live-MOEX tests; unresolved production evidence stays PARTIAL/MISSING.
const current=Gate.assess({
  regression:{status:'PASS',verified:true,evidence:'R1.8.25 CI regression suite'},
  liveMoex:{status:'PASS',verified:true,evidence:'R1.8.25 GitHub runner TQBR live probe'},
  browserSmoke:{status:'PASS',verified:true,evidence:'R1.8.25 Chromium smoke + MOEX fail-closed'},
  sberValuation:{status:'PARTIAL',verified:false,evidence:'Common-equity/share basis and P/B remain unresolved'},
  issuerRiskCoverage:{status:'PARTIAL',verified:false,evidence:'YDEX verified; X5, MOEX and SBER issuer-risk registries remain LOCK'},
  portfolioContextSafety:{status:'PASS',verified:true,evidence:'Recommendation safety + explicit portfolio-context regression'},
  security:{status:'MISSING',verified:false,evidence:'No production security gate proving 0 critical/high defects yet'}
});

assert.equal(current.status,'HOLD');
assert.equal(current.verified,false);
assert.equal(current.decision,'DO_NOT_RELEASE');
assert(current.blockers.includes('sberValuation'));
assert(current.blockers.includes('issuerRiskCoverage'));
assert(current.blockers.includes('security'));
assert(!current.blockers.includes('regression'));
assert(!current.blockers.includes('liveMoex'));
assert(!current.blockers.includes('browserSmoke'));
assert(!current.blockers.includes('portfolioContextSafety'));
console.log('R1.8.26 CURRENT STATUS: HOLD');
console.log('Blockers:', current.blockers.join(', '));
