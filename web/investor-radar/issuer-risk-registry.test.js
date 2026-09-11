const assert=require('assert');
const R=require('./issuer-risk-registry.js');

let a=R.audit('YDEX');
assert.equal(a.sourceExists,true);
assert.equal(a.riskVerified,true);
assert.equal(a.status,'VERIFIED');
assert.equal(R.get('YDEX').issuer.verified,true);

for(const t of ['X5','MOEX']){
  const r=R.audit(t);
  assert.equal(r.sourceExists,true,`${t} source must exist`);
  assert.equal(r.riskVerified,false,`${t} source presence must not imply risk verification`);
  assert.equal(r.status,'LOCK');
  assert.equal(R.get(t).issuer.verified,false);
  assert.equal(R.get(t).issuer.status,'LOCK');
}

a=R.audit('SBER');
assert.equal(a.riskVerified,false);
assert.equal(R.get('SBER').issuer.verified,false);

a=R.audit('UNKNOWN');
assert.equal(a.sourceExists,false);
assert.equal(a.riskVerified,false);
assert.equal(a.status,'LOCK');
assert.equal(R.get('UNKNOWN').sourceStatus,'MISSING');

console.log('R1.8.25 issuer risk registry semantics: PASS');
