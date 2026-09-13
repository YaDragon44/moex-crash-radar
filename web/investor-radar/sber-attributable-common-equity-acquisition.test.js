const assert=require('assert');
const Gate=require('./sber-attributable-common-equity-acquisition.js');

const locked=Gate.unresolved();
assert.strictEqual(locked.status,'PARTIAL');
assert.strictEqual(locked.verified,false);
assert(locked.missing.includes('primary_source'));
assert(locked.missing.includes('attributable_common_equity'));
assert(locked.missing.includes('treasury_common_shares'));
assert(locked.missing.includes('preferred_treatment'));
assert.strictEqual(locked.bvps,null);

const ok=Gate.assess({
 primarySourceVerified:true,
 primarySourceUrl:'https://example.test/primary',
 attributableEquityToShareholdersRub:10000,
 attributableCommonEquityRub:9500,
 commonAllocationMethodVerified:true,
 commonIssueSize:100,
 treasuryCommonShares:5,
 commonSharesOutstanding:95,
 preferredTreatmentVerified:true,
 preferredTreatmentSourceUrl:'https://example.test/charter',
 asOf:'2025-12-31'
});
assert.strictEqual(ok.status,'VERIFIED');
assert.strictEqual(ok.bvps,100);

const mismatch=Gate.assess({
 primarySourceVerified:true,
 primarySourceUrl:'https://example.test/primary',
 attributableEquityToShareholdersRub:10000,
 attributableCommonEquityRub:9500,
 commonAllocationMethodVerified:true,
 commonIssueSize:100,
 treasuryCommonShares:5,
 commonSharesOutstanding:96,
 preferredTreatmentVerified:true,
 preferredTreatmentSourceUrl:'https://example.test/charter',
 asOf:'2025-12-31'
});
assert.strictEqual(mismatch.status,'PARTIAL');
assert(mismatch.missing.includes('share_reconciliation'));

console.log('SBER Attributable Common Equity Acquisition Gate: PASS');
