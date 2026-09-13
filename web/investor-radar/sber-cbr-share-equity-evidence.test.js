const assert=require('assert');
const E=require('./sber-cbr-share-equity-evidence.js');

const r=E.assess();
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.treasuryTreatmentVerified,true);
assert.equal(r.treasuryCommonShares,0);
assert.equal(r.commonSharesOutstanding,21586948000);
assert.equal(r.commonIssueSize,21586948000);
assert.equal(r.preferredIssueSize,1000000000);
assert.equal(r.commonEquityAttributableVerified,false);
assert.equal(r.preferredTreatmentVerified,false);
assert.equal(r.proxyOnly,true);
assert(Math.abs(r.statutoryAllShareBvpsProxy-359.28186844898215)<1e-9);

const bad=E.assess({commonIssueSize:0});
assert.equal(bad.status,'PARTIAL');
assert.equal(bad.verified,false);
assert(bad.missing.includes('common_issue_size'));

console.log('R1.8.34 SBER CBR share/equity evidence: PASS');
