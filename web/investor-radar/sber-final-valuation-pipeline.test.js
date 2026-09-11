const assert=require('assert');
const P=require('./sber-final-valuation-pipeline.js');
const C=require('./sber-valuation-completeness-gate.js');
const V={status:'VERIFIED',verified:true};

let r=P.build({completenessGate:C,price:300,priceVerified:true,peRuntime:V,bankValuation:V,bankQuality:{...V,traffic:'YELLOW'},equityAttribution:{status:'PARTIAL',verified:false},valuationLabel:'FAIR',action:'ДЕРЖАТЬ'});
assert.equal(r.status,'PARTIAL');
assert.equal(r.action,'НАБЛЮДАТЬ');
assert.equal(r.confidence,'НИЗКАЯ');
assert.equal(r.valuation,'INSUFFICIENT_DATA');
assert(r.blockers.includes('common_equity_share_basis'));

r=P.build({completenessGate:C,price:null,priceVerified:false,peRuntime:V,bankValuation:V,bankQuality:{...V,traffic:'GREEN'},equityAttribution:V});
assert.equal(r.status,'PARTIAL');
assert(r.blockers.includes('current_price'));
assert.equal(r.currentPrice,null);

r=P.build({completenessGate:C,price:300,priceVerified:true,peRuntime:V,bankValuation:V,bankQuality:{...V,traffic:'YELLOW'},equityAttribution:V,valuationLabel:'FAIR',action:'ДЕРЖАТЬ',confidence:'СРЕДНЯЯ'});
assert.equal(r.status,'VERIFIED');
assert.equal(r.recommendationEligible,true);
assert.equal(r.valuation,'FAIR');
assert.equal(r.action,'ДЕРЖАТЬ');
assert.equal(r.traffic,'YELLOW');
assert.deepEqual(r.blockers,[]);

console.log('R1.8.23 SBER final valuation pipeline tests: PASS');
