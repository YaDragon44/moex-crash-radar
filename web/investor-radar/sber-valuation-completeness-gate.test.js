const assert=require('assert');
const G=require('./sber-valuation-completeness-gate.js');

const V={status:'VERIFIED',verified:true};
let r=G.assess({peRuntime:V,bankValuation:V,bankQuality:{...V,traffic:'YELLOW'},equityAttribution:{status:'PARTIAL',verified:false}});
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert.equal(r.traffic,'GRAY');
assert.equal(r.valuationLabel,'INSUFFICIENT_DATA');
assert(r.missing.includes('common_equity_share_basis_or_reported_bvps'));
assert.equal(r.denominatorSource,'MISSING');
assert.equal(r.message,'Недостаточно данных для обоснованного вывода');

r=G.assess({peRuntime:V,bankValuation:V,bankQuality:{...V,traffic:'YELLOW'},equityAttribution:{status:'PARTIAL',verified:false},reportedBvps:V,valuationLabel:'FAIR'});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.traffic,'YELLOW');
assert.equal(r.valuationLabel,'FAIR');
assert.equal(r.denominatorSource,'ISSUER_REPORTED_COMMON_BVPS');
assert.deepEqual(r.missing,[]);

r=G.assess({peRuntime:V,bankValuation:V,bankQuality:{...V,traffic:'YELLOW'},equityAttribution:V,valuationLabel:'FAIR'});
assert.equal(r.status,'VERIFIED');
assert.equal(r.denominatorSource,'RECONSTRUCTED_COMMON_EQUITY_SHARE_BASIS');

r=G.assess({peRuntime:V,bankValuation:{status:'PARTIAL',verified:false},bankQuality:{...V,traffic:'GREEN'},reportedBvps:V});
assert.equal(r.status,'PARTIAL');
assert(r.missing.includes('pb_bank_valuation'));

console.log('R1.8.46 SBER valuation completeness gate tests: PASS');
