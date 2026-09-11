const assert=require('assert');
const G=require('./exchange-issuer-risk-gate.js');

let r=G.assess({});
assert.equal(r.status,'LOCK');
assert.equal(r.verified,false);

r=G.assess({
 verified:true,
 feeIncomeGrowthPct:24.8,
 netProfitGrowthPct:4.7,
 adjustedEbitdaMarginPct:67.6,
 opexGrowthPct:10.4,
 cashPositionBln:194,
 debtBln:0,
 ratingVerified:true,
 rating:'ruAAA',
 ratingOutlook:'stable',
 ratingSource:'MOEX Q2 2026 official results / Expert RA reaffirmation disclosed by issuer',
 source:'Moscow Exchange Q2 2026 IFRS results',
 sourceUrl:'https://www.moex.com/n103659',
 asOf:'2026-06-30'
});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.riskLevel,'LOW');
assert.equal(r.thesisBroken,false);
assert.equal(r.coverage,'EXCHANGE_FEES_PROFIT_MARGIN_COSTS_LIQUIDITY_RATING');

const medium=G.assess({...r,verified:true,feeIncomeGrowthPct:-1,ratingVerified:true,ratingSource:'x'});
assert.equal(medium.riskLevel,'MEDIUM');
const high=G.assess({...r,verified:true,netProfitGrowthPct:-45,ratingVerified:true,ratingSource:'x'});
assert.equal(high.riskLevel,'HIGH');

console.log('R1.8.30 exchange issuer risk gate: PASS');
