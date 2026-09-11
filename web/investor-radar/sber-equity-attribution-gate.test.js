const assert=require('assert');
const G=require('./sber-equity-attribution-gate.js');
const CBR=require('./sber-cbr-share-equity-evidence.js');

let r=G.unresolved();
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert(!r.missing.includes('treasury_common_shares'));
assert(!r.missing.includes('common_shares_outstanding'));
assert(r.missing.includes('attributable_common_equity'));
assert(r.missing.includes('preferred_share_treatment'));

const cbr=CBR.assess();
r=G.fromCbrEvidence(cbr,{});
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert.equal(r.reconciled,true);
assert.equal(r.treasuryCommonShares,0);
assert.equal(r.commonSharesOutstanding,21586948000);
assert.deepEqual(r.missing,['attributable_common_equity','preferred_share_treatment']);

r=G.fromCbrEvidence(cbr,{
 attributableCommonEquityRub:9500,
 preferredTreatmentVerified:true,
 equitySource:'PRIMARY_IFRS'
});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.reconciled,true);
assert.equal(r.commonSharesOutstanding,21586948000);
assert.equal(r.attributableCommonEquityRub,9500);

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

console.log('R1.8.34 SBER equity attribution gate tests: PASS');
