const assert=require('assert');
const G=require('./production-readiness-gate.js');
const P={status:'PASS',verified:true,evidence:'synthetic regression fixture'};
function full(overrides={}){return Object.assign({regression:P,liveMoex:P,browserSmoke:P,sberValuation:P,issuerRiskCoverage:P,issuerRiskProvenance:P,decisionIntegrity:P,portfolioContextSafety:P,security:P,architectureSimplicity:P},overrides);}

let r=G.assess(full());
assert.equal(r.status,'READY');
assert.equal(r.verified,true);
assert.equal(r.decision,'RELEASE_CANDIDATE_ELIGIBLE');
assert.deepEqual(r.blockers,[]);
assert.equal(r.completionPct,100);
assert.equal(r.passCount,10);

r=G.assess(full({sberValuation:{status:'PARTIAL',verified:false,evidence:'common BVPS basis unresolved'}}));
assert.equal(r.status,'HOLD');
assert.equal(r.verified,false);
assert.equal(r.decision,'DO_NOT_RELEASE');
assert.deepEqual(r.blockers,['sberValuation']);
assert.equal(r.completionPct,90);
assert.equal(r.message,'Недостаточно данных для обоснованного вывода');

r=G.assess(full({issuerRiskProvenance:{status:'FAIL',verified:false}}));
assert(r.blockers.includes('issuerRiskProvenance'));
r=G.assess(full({decisionIntegrity:{status:'MISSING',verified:false}}));
assert(r.blockers.includes('decisionIntegrity'));
r=G.assess(full({architectureSimplicity:{status:'FAIL',verified:false}}));
assert(r.blockers.includes('architectureSimplicity'));
r=G.assess(full({security:undefined}));
assert(r.blockers.includes('security'));

console.log('R1.8.36 production readiness re-audit gate tests: PASS');
