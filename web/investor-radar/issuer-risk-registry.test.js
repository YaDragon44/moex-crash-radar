const assert=require('assert');
const R=require('./issuer-risk-registry.js');

for(const t of ['YDEX','SBER','X5','MOEX']){
  const a=R.audit(t);
  assert.equal(a.sourceExists,true,`${t} source must exist`);
  assert.equal(a.riskVerified,true,`${t} issuer risk must be verified`);
  assert.equal(a.status,'VERIFIED');
  assert.equal(R.get(t).issuer.verified,true);
}
assert.equal(R.get('SBER').issuer.coverage,'BANK_ROE_CAPITAL_ASSET_QUALITY');
assert.equal(R.get('SBER').issuer.riskLevel,'MEDIUM');
assert.equal(R.get('SBER').issuer.thesisBroken,false);
assert.equal(R.get('X5').issuer.coverage,'RETAIL_GROWTH_MARGIN_LEVERAGE_PROFIT_RATING');
assert.equal(R.get('X5').issuer.riskLevel,'MEDIUM');
assert.equal(R.get('X5').issuer.thesisBroken,false);
assert.equal(R.get('X5').issuer.ratingSources.length,2);
assert.equal(R.get('MOEX').issuer.coverage,'EXCHANGE_FEES_PROFIT_MARGIN_COSTS_LIQUIDITY_RATING');
assert.equal(R.get('MOEX').issuer.riskLevel,'LOW');
assert.equal(R.get('MOEX').issuer.thesisBroken,false);
assert.equal(R.get('MOEX').sanctionsRegulatory.critical,true,'MOEX sanctions risk must remain separately visible');

let a=R.audit('UNKNOWN');
assert.equal(a.sourceExists,false);
assert.equal(a.riskVerified,false);
assert.equal(a.status,'LOCK');
assert.equal(R.get('UNKNOWN').sourceStatus,'MISSING');

console.log('R1.8.30 issuer risk registry coverage 4/4: PASS');
