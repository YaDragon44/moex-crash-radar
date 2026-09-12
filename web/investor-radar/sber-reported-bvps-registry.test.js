'use strict';
const assert=require('assert');
const R=require('./sber-reported-bvps-registry.js');
let r=R.assess();
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.bookValuePerShare,390.02);
assert.equal(r.locator,'page:132:line:49');
assert.equal(r.supportingEquity.valueRubBn2025,8351.6);

r=R.assess({...R.EVIDENCE,metric:'TOTAL_EQUITY_PER_SHARE'});
assert.equal(r.status,'PARTIAL');
assert(r.missing.includes('common_share_semantics'));

r=R.assess({...R.EVIDENCE,documentSha256:null});
assert.equal(r.status,'PARTIAL');
assert(r.missing.includes('traceability'));
console.log('R1.8.44 SBER reported BVPS evidence: PASS');
