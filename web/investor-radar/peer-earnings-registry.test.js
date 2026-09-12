const assert=require('assert');
const R=require('./peer-earnings-registry.js');
for(const t of ['VTBR','T','LENT']) assert.equal(R.usable(t),true);
assert.equal(R.get('VTBR').eps,79.4);
assert.equal(R.get('T').rawEps,688.72);
assert.equal(R.get('T').eps,68.872);
assert.equal(R.get('T').metric,'EPS_SPLIT_ADJUSTED');
assert.equal(R.get('T').corporateAction.ratioOld,1);
assert.equal(R.get('T').corporateAction.ratioNew,10);
assert.equal(R.get('T').corporateAction.effectiveDate,'2026-04-17');
assert.equal(R.basisOk(R.get('T')),true);
assert.equal(R.get('LENT').eps,0.303);
for(const t of ['VTBR','T','LENT']) assert.equal(R.get(t).status,'VERIFIED');
for(const t of ['VKCO','OZON','MGNT']){assert.equal(R.usable(t),false);assert.equal(R.get(t).verified,true);assert.equal(R.get(t).status,'VERIFIED_EXCLUDED');assert(R.audit(t).missing.includes('positive_eps'));}
assert.equal(R.get('VKCO').eps,-63);
assert.equal(R.get('OZON').eps,-36.1);
assert.equal(R.get('MGNT').eps,-455.28);
assert.equal(R.audit('UNKNOWN').usable,false);
console.log('R1.8.46 exact EPS + corporate action basis tests: PASS');
