const assert=require('assert');
const G=require('./sber-book-value-gate.js');

let r=G.fromTotalCapital();
assert.equal(r.status,'LOCK');
assert.equal(r.verified,false);
assert(r.missing.includes('common_equity_attributable'));
assert(r.missing.includes('preferred_share_treatment'));

r=G.assess({
  verified:true,
  commonEquityAttributableRub:8.0e12,
  commonSharesOutstanding:2.0e10,
  price:320,
  preferredTreatmentVerified:true,
  equitySource:'PRIMARY',shareSource:'PRIMARY',priceSource:'MOEX ISS',asOf:'2026-09-10'
});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.bvps,400);
assert.equal(r.pb,0.8);

r=G.assess({verified:true,commonEquityAttributableRub:8e12,commonSharesOutstanding:2e10,price:320,preferredTreatmentVerified:false,equitySource:'PRIMARY',shareSource:'PRIMARY',priceSource:'MOEX ISS',asOf:'2026-09-10'});
assert.equal(r.status,'LOCK');
assert(r.missing.includes('preferred_share_treatment'));

console.log('R1.8.19 SBER book value gate tests: PASS');
