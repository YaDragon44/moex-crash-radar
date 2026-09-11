const assert=require('assert');
const R=require('./issuer-risk-registry.js');

const expected={
  YDEX:'TECH_ISSUER_RISK_GATE_R1.8.32',
  SBER:'BANK_ISSUER_RISK_GATE_R1.8.28',
  X5:'RETAIL_ISSUER_RISK_GATE_R1.8.29',
  MOEX:'EXCHANGE_ISSUER_RISK_GATE_R1.8.30'
};

for(const t of Object.keys(expected)){
  const a=R.audit(t);
  assert.equal(a.sourceExists,true,`${t} source must exist`);
  assert.equal(a.verifiedClaim,true,`${t} registry claims VERIFIED`);
  assert.equal(a.riskVerified,true,`${t} issuer risk must be reproducibly verified`);
  assert.equal(a.crossDomainOk,true,`${t} sanctions semantics must stay delegated`);
  assert.equal(a.sectorGateOk,true,`${t} sector gate binding must match`);
  assert.equal(a.expectedGate,expected[t]);
  assert.equal(a.derivedBy,expected[t]);
  assert.equal(a.status,'VERIFIED');
  assert.equal(R.get(t).issuer.verified,true);
  assert.equal(R.get(t).issuer.derivedBy,expected[t]);
  assert.equal(R.get(t).sanctionsRegulatory.status,'DELEGATED');
  assert.equal(R.get(t).sanctionsRegulatory.critical,undefined);
}

assert.equal(R.get('SBER').issuer.coverage,'BANK_ROE_CAPITAL_ASSET_QUALITY');
assert.equal(R.get('X5').issuer.coverage,'RETAIL_GROWTH_MARGIN_LEVERAGE_PROFIT_RATING');
assert.equal(R.get('MOEX').issuer.coverage,'EXCHANGE_FEES_PROFIT_MARGIN_COSTS_LIQUIDITY_RATING');
assert.equal(R.get('YDEX').issuer.coverage,'TECH_GROWTH_MARGIN_LEVERAGE_LIQUIDITY_PROFITABILITY');

const all=R.auditAll();
assert.equal(all.ok,true);
assert.equal(all.coverage,'4/4');
assert.deepEqual(all.errors,[]);
assert.equal(all.rows.every(x=>x.riskVerified),true);

let a=R.audit('UNKNOWN');
assert.equal(a.sourceExists,false);
assert.equal(a.riskVerified,false);
assert.equal(a.status,'LOCK');
assert.equal(R.get('UNKNOWN').sourceStatus,'MISSING');

// Negative regression: VERIFIED without exact sector provenance must fail closed.
const original=R.REGISTRY.X5.issuer.derivedBy;
R.REGISTRY.X5.issuer.derivedBy='MANUAL_VERIFIED';
a=R.audit('X5');
assert.equal(a.verifiedClaim,true);
assert.equal(a.sectorGateOk,false);
assert.equal(a.riskVerified,false);
assert.equal(a.reason,'sector_gate_binding_missing');
R.REGISTRY.X5.issuer.derivedBy=original;

console.log('R1.8.33 issuer sector gate coverage audit 4/4: PASS');
