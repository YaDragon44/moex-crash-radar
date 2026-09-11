const assert=require('assert');
const G=require('./production-readiness-gate.js');
const P={status:'PASS',verified:true,evidence:'synthetic regression fixture'};

let r=G.assess({regression:P,liveMoex:P,browserSmoke:P,sberValuation:P,issuerRiskCoverage:P,portfolioContextSafety:P,security:P});
assert.equal(r.status,'READY');
assert.equal(r.verified,true);
assert.equal(r.decision,'RELEASE_CANDIDATE_ELIGIBLE');
assert.deepEqual(r.blockers,[]);

r=G.assess({regression:P,liveMoex:P,browserSmoke:P,sberValuation:{status:'PARTIAL',verified:false},issuerRiskCoverage:{status:'PARTIAL',verified:false},portfolioContextSafety:P,security:P});
assert.equal(r.status,'HOLD');
assert.equal(r.verified,false);
assert.equal(r.decision,'DO_NOT_RELEASE');
assert(r.blockers.includes('sberValuation'));
assert(r.blockers.includes('issuerRiskCoverage'));
assert.equal(r.message,'Недостаточно данных для обоснованного вывода');

r=G.assess({regression:P,liveMoex:P,browserSmoke:P,sberValuation:P,issuerRiskCoverage:P,portfolioContextSafety:P});
assert.equal(r.status,'HOLD');
assert(r.blockers.includes('security'));

console.log('R1.8.26 production readiness gate tests: PASS');
