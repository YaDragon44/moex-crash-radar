const assert=require('assert');
const G=require('./sber-equity-attribution-gate.js');

let r=G.unresolved();
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert(r.missing.includes('treasury_common_shares'));
assert(r.missing.includes('attributable_common_equity'));

r=G.assess({
 verified:true,
 commonIssueSize:100,
 treasuryCommonShares:5,
 commonSharesOutstanding:95,
 attributableCommonEquityRub:9500,
 preferredTreatmentVerified:true,
 equitySource:'PRIMARY_IFRS',shareSource:'PRIMARY_REPORT',treasurySource:'PRIMARY_IFRS',asOf:'2025-12-31'
});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.reconciled,true);
assert.equal(r.commonSharesOutstanding,95);
assert.equal(r.attributableCommonEquityRub,9500);

r=G.assess({
 verified:true,
 commonIssueSize:100,
 treasuryCommonShares:5,
 commonSharesOutstanding:96,
 attributableCommonEquityRub:9500,
 preferredTreatmentVerified:true,
 equitySource:'PRIMARY_IFRS',shareSource:'PRIMARY_REPORT',treasurySource:'PRIMARY_IFRS',asOf:'2025-12-31'
});
assert.equal(r.status,'PARTIAL');
assert(r.missing.includes('share_reconciliation'));

console.log('R1.8.21 SBER equity attribution gate tests: PASS');
