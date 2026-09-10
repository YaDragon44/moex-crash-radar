const assert=require('assert');
const R=require('./peer-earnings-registry.js');
for(const t of ['VTBR','T','LENT']) assert.equal(R.usable(t),true);
assert.equal(R.get('VTBR').eps,79.4);
assert.equal(R.get('T').eps,688.72);
assert.equal(R.get('LENT').eps,0.303);
for(const t of ['VTBR','T','LENT']) assert.equal(R.get(t).status,'VERIFIED');
for(const t of ['VKCO','OZON','MGNT']){assert.equal(R.usable(t),false);assert.equal(R.get(t).verified,true);assert.equal(R.get(t).status,'VERIFIED_EXCLUDED');assert(R.audit(t).missing.includes('positive_eps'));}
assert.equal(R.get('VKCO').eps,-63);
assert.equal(R.get('OZON').eps,-36.1);
assert.equal(R.get('MGNT').eps,-455.28);
assert.equal(R.audit('UNKNOWN').usable,false);
console.log('R1.8.13 exact EPS verification tests: PASS');
