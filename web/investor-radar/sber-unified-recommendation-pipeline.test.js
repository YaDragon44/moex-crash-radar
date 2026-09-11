const assert=require('assert');
const P=require('./sber-unified-recommendation-pipeline.js');
const R=require('./recommendation-engine.js');
const C=require('./sber-valuation-completeness-gate.js');

const V={status:'VERIFIED',verified:true};
const PART={status:'PARTIAL',verified:false};
function base(){return {
 recommendationEngine:R,completenessGate:C,
 peRuntime:V,bankValuation:V,bankQuality:{...V,traffic:'YELLOW'},equityAttribution:V,
 valuationLabel:'FAIR',price:100,
 fundamental:{verified:true,growthCagr:10},
 valuation:{status:'VERIFIED',low:110,high:130},
 risk:{verified:true,score:40,thesisBroken:false,items:['risk'],issuerProvenance:{verified:true,derivedBy:'BANK_ISSUER_RISK_GATE_R1.8.28'},sanctions:{verified:false,level:'UNKNOWN'}},
 portfolio:{held:true},facts:['fact1','fact2']
};}
let x=base(),r=P.build(x);
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.decision.action,'ДОБИРАТЬ');
assert.equal(r.completeness.status,'VERIFIED');

x=base();x.equityAttribution=PART;r=P.build(x);
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert.equal(r.decision.action,'НАБЛЮДАТЬ');
assert.equal(r.decision.light,'СЕРЫЙ');
assert(r.missing.includes('common_equity_share_basis'));
assert(r.missing.includes('sber_full_valuation_completeness'));

x=base();delete x.portfolio;r=P.build(x);
assert.equal(r.status,'PARTIAL');
assert.equal(r.decision.action,'НАБЛЮДАТЬ');
assert(r.missing.includes('portfolio_context'));

x=base();x.risk.thesisBroken=true;r=P.build(x);
assert.equal(r.status,'PARTIAL');
assert.equal(r.decision.action,'ПРОДАВАТЬ');
assert.equal(r.decision.light,'КРАСНЫЙ');

x=base();x.risk.issuerProvenance={verified:false};r=P.build(x);
assert.equal(r.status,'PARTIAL');
assert.equal(r.decision.action,'НАБЛЮДАТЬ');
assert(r.missing.includes('issuer_risk_provenance_missing'));

x=base();delete x.recommendationEngine;r=P.build(x);
assert.equal(r.status,'LOCK');assert.equal(r.decision,null);assert(r.missing.includes('recommendation_engine'));
console.log('R1.8.34 SBER unified recommendation pipeline tests: PASS');
