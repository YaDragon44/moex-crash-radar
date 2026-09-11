const assert=require('assert');
const R=require('./issuer-risk-registry.js');

for(const t of ['YDEX','SBER','X5','MOEX']){
  const a=R.audit(t);
  assert.equal(a.sourceExists,true,`${t} source must exist`);
  assert.equal(a.riskVerified,true,`${t} issuer risk must be verified`);
  assert.equal(a.crossDomainOk,true,`${t} sanctions semantics must stay delegated`);
  assert.equal(a.status,'VERIFIED');
  assert.equal(R.get(t).issuer.verified,true);
  assert.equal(R.get(t).sanctionsRegulatory.status,'DELEGATED');
  assert.equal(R.get(t).sanctionsRegulatory.critical,undefined);
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
assert.equal(R.get('MOEX').sanctionsRegulatory.material,null,'issuer registry must not duplicate sanctions facts');
assert.equal(R.get('MOEX').sanctionsRegulatory.designated,null,'issuer registry must delegate designation facts');

const all=R.auditAll();
assert.equal(all.ok,true);
assert.deepEqual(all.errors,[]);

let a=R.audit('UNKNOWN');
assert.equal(a.sourceExists,false);
assert.equal(a.riskVerified,false);
assert.equal(a.crossDomainOk,true);
assert.equal(a.status,'LOCK');
assert.equal(R.get('UNKNOWN').sourceStatus,'MISSING');
assert.equal(R.get('UNKNOWN').sanctionsRegulatory.critical,undefined);

console.log('R1.8.31 issuer/sanctions cross-domain semantics: PASS');
