const assert=require('assert');
const R=require('./sber-share-basis-registry.js');

const a=R.audit({});
assert.equal(a.status,'PARTIAL');
assert.equal(a.verified,false);
assert.equal(a.commonIssueSize,21586948000);
assert.equal(a.preferredIssueSize,1000000000);
assert.equal(a.totalIssuedShares,22586948000);
assert(a.missing.includes('common_shares_outstanding'));
assert(a.missing.includes('treasury_share_treatment'));
assert(a.missing.includes('attributable_common_equity'));

const b=R.audit({
 commonSharesOutstandingVerified:true,
 commonSharesOutstanding:21586948000,
 treasuryTreatmentVerified:true,
 attributableCommonEquityVerified:true,
 attributableCommonEquityBnRub:7000
});
assert.equal(b.status,'VERIFIED');
assert.equal(b.verified,true);
assert.deepEqual(b.missing,[]);

console.log('R1.8.20 SBER share basis registry tests: PASS');
