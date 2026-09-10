const assert=require('assert');
const R=require('./risk-layer.js');

const flat=Array.from({length:130},(_,i)=>({close:100}));
let a=R.assess(flat);
assert.equal(a.marketVerified,true);
assert.equal(a.verified,false);
assert.equal(a.status,'PARTIAL');
assert.equal(a.metrics.maxDrawdown,0);
assert.equal(a.metrics.annualizedVolatility,0);
assert.equal(a.score,0);
assert(a.missing.includes('liquidity'));

const short=Array.from({length:50},()=>({close:100}));
a=R.assess(short);
assert.equal(a.marketVerified,false);
assert.equal(a.status,'LOCK');
assert.equal(a.score,null);

const path=[]; for(let i=0;i<65;i++)path.push({close:100+i}); for(let i=0;i<65;i++)path.push({close:164-i});
a=R.assess(path);
assert.equal(a.marketVerified,true);
assert(a.metrics.maxDrawdown<0);
assert(Number.isFinite(a.metrics.annualizedVolatility));
assert(Number.isFinite(a.score));

assert.equal(R.classify(20),'LOW');
assert.equal(R.classify(50),'MEDIUM');
assert.equal(R.classify(80),'HIGH');
assert.equal(R.marketRiskScore(60,-60),100);

console.log('R1.8.2 market risk layer tests: PASS');
