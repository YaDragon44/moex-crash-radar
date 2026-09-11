const assert=require('assert');
const P=require('./sber-preferred-treatment-evidence.js');

const r=P.assess();
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert.equal(r.preferredTreatmentVerified,false);
assert.equal(r.dividendEqualityVerified,true);
assert.equal(r.preferredSecurityVerified,true);
assert(r.missing.includes('current_charter_liquidation_rights'));
assert(r.missing.includes('current_charter_equity_priority'));
assert(r.missing.includes('equity_allocation_method'));
assert.equal(P.EVIDENCE.preferredIssueSize,1000000000);
assert.equal(P.EVIDENCE.preferredFaceValueRub,3);
assert.equal(P.EVIDENCE.commonDividend2025Rub,37.64);
assert.equal(P.EVIDENCE.preferredDividend2025Rub,37.64);
console.log('R1.8.35 SBER preferred treatment evidence: PASS');
