const assert=require('assert');
const G=require('./tech-issuer-risk-gate.js');

let r=G.assess({
 verified:true,
 revenueGrowthPct:31.7,
 adjustedEbitdaMarginPct:19.5,
 adjustedNetDebtToEbitda:0.2,
 cashAndShortTermDepositsBln:250.2,
 adjustedNetProfitGrowthPct:40.1,
 source:'Yandex IR FY2025',
 sourceUrl:'https://ir.yandex.ru/financial-releases?report=q4&year=2025',
 asOf:'2025-12-31'
});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.riskLevel,'LOW');
assert.equal(r.critical,false);
assert.equal(r.thesisBroken,false);
assert.equal(r.coverage,'TECH_GROWTH_MARGIN_LEVERAGE_LIQUIDITY_PROFITABILITY');

r=G.assess({verified:true,revenueGrowthPct:5,adjustedEbitdaMarginPct:14,adjustedNetDebtToEbitda:1.7,cashAndShortTermDepositsBln:100,adjustedNetProfitGrowthPct:-5,source:'primary',sourceUrl:'https://example.test',asOf:'2026-01-01'});
assert.equal(r.riskLevel,'MEDIUM');

r=G.assess({verified:true,revenueGrowthPct:-35,adjustedEbitdaMarginPct:8,adjustedNetDebtToEbitda:4.2,cashAndShortTermDepositsBln:50,adjustedNetProfitGrowthPct:-65,source:'primary',sourceUrl:'https://example.test',asOf:'2026-01-01'});
assert.equal(r.riskLevel,'HIGH');
assert.equal(r.critical,true);
assert.equal(r.thesisBroken,false);

r=G.assess({verified:false});
assert.equal(r.status,'LOCK');
assert.equal(r.verified,false);
assert(r.missing.includes('verified_inputs'));
assert(r.missing.includes('source_metadata'));

console.log('R1.8.32 tech issuer risk gate tests: PASS');
