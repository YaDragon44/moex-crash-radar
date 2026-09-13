const assert=require('assert');
const G=require('./bank-issuer-risk-gate.js');

let r=G.assess({verified:true,roe:22.7,cet1:12.3,npl:4.9,costOfRisk:1.30,source:'MOEX issuer financials / Sber disclosure',sourceUrl:'https://www.moex.com/en/stocks/sber',asOf:'2025-12-31'});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.riskLevel,'MEDIUM');
assert.equal(r.critical,false);
assert.equal(r.thesisBroken,false);
assert.equal(r.coverage,'BANK_ROE_CAPITAL_ASSET_QUALITY');

r=G.assess({verified:true,roe:10,cet1:9,npl:7,costOfRisk:2.2,source:'fixture',sourceUrl:'https://example.com',asOf:'2025-12-31'});
assert.equal(r.status,'VERIFIED');
assert.equal(r.riskLevel,'HIGH');
assert.equal(r.thesisBroken,false);

r=G.assess({verified:false,roe:22.7,cet1:12.3,npl:4.9,costOfRisk:1.3});
assert.equal(r.status,'LOCK');
assert.equal(r.verified,false);
assert(r.missing.includes('verified_inputs'));
assert(r.missing.includes('source_metadata'));

console.log('R1.8.28 bank issuer risk gate tests: PASS');
