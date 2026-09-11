const assert=require('assert');
const R=require('./issuer-risk-registry.js');

for(const t of ['YDEX','SBER']){
  const a=R.audit(t);
  assert.equal(a.sourceExists,true,`${t} source must exist`);
  assert.equal(a.riskVerified,true,`${t} issuer risk must be verified`);
  assert.equal(a.status,'VERIFIED');
  assert.equal(R.get(t).issuer.verified,true);
}
assert.equal(R.get('SBER').issuer.coverage,'BANK_ROE_CAPITAL_ASSET_QUALITY');
assert.equal(R.get('SBER').issuer.riskLevel,'MEDIUM');
assert.equal(R.get('SBER').issuer.thesisBroken,false);

for(const t of ['X5','MOEX']){
  const r=R.audit(t);
  assert.equal(r.sourceExists,true,`${t} source must exist`);
  assert.equal(r.riskVerified,false,`${t} source presence must not imply risk verification`);
  assert.equal(r.status,'LOCK');
  assert.equal(R.get(t).issuer.verified,false);
  assert.equal(R.get(t).issuer.status,'LOCK');
}

let a=R.audit('UNKNOWN');
assert.equal(a.sourceExists,false);
assert.equal(a.riskVerified,false);
assert.equal(a.status,'LOCK');
assert.equal(R.get('UNKNOWN').sourceStatus,'MISSING');

console.log('R1.8.28 issuer risk registry coverage: PASS');
