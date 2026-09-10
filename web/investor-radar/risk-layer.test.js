const assert=require('assert');
const R=require('./risk-layer.js');

const flat=Array.from({length:130},()=>({close:100}));
let a=R.assess(flat);
assert.equal(a.marketVerified,true);
assert.equal(a.verified,false);
assert.equal(a.status,'PARTIAL');
assert.equal(a.metrics.maxDrawdown,0);
assert.equal(a.metrics.annualizedVolatility,0);
assert.equal(a.score,0);
assert(a.missing.includes('liquidity'));
assert(a.missing.includes('issuer_fundamental_risk'));
assert(a.missing.includes('sanctions_regulatory_risk'));

const liq={verified:true,turnoverRub:600e6,numTrades:6000};
a=R.assess(flat,liq,{verified:false},{verified:false});
assert.equal(a.liquidityVerified,true);
assert.equal(a.verified,false);
assert.equal(a.metrics.liquidityScore,0);
assert(!a.missing.includes('liquidity'));

// Full verification only when all four risk domains are explicitly verified.
a=R.assess(flat,liq,{verified:true,critical:false},{verified:true,critical:false});
assert.equal(a.verified,true);
assert.equal(a.status,'VERIFIED');
assert.equal(a.scope,'FULL');
assert.equal(a.score,0);
assert.equal(a.missing.length,0);

// Regulatory/issuer critical risk overrides the numeric market/liquidity score.
a=R.assess(flat,liq,{verified:true,critical:true},{verified:true,critical:false});
assert.equal(a.critical,true);

const short=Array.from({length:50},()=>({close:100}));
a=R.assess(short,liq,{verified:true},{verified:true});
assert.equal(a.marketVerified,false);
assert.equal(a.status,'LOCK');
assert.equal(a.score,null);

assert.equal(R.classify(20),'LOW');
assert.equal(R.classify(50),'MEDIUM');
assert.equal(R.classify(80),'HIGH');
assert.equal(R.marketRiskScore(60,-60),100);
assert.equal(R.liquidityRiskScore(600e6,6000),0);
assert.equal(R.liquidityRiskScore(1e6,50),100);

console.log('R1.8.3 full risk gate tests: PASS');
