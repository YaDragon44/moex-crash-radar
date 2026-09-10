const assert=require('assert');
const P=require('./peer-universe-registry.js');
for(const t of ['SBER','YDEX','X5']){const x=P.validate(t);assert.equal(x.eligible,true);assert(x.peers.length>=2);}
const m=P.validate('MOEX');assert.equal(m.eligible,false);assert.equal(m.status,'LIMITED_UNIVERSE');assert.equal(m.peers.length,0);
assert.equal(P.get('SBER').sector,'BANKS');assert.equal(P.get('YDEX').sector,'INTERNET_TECH');assert.equal(P.get('X5').sector,'FOOD_RETAIL');assert.equal(P.get('MOEX').sector,'EXCHANGE_INFRASTRUCTURE');
assert.equal(P.validate('UNKNOWN').eligible,false);
console.log('R1.8.10 peer universe tests: PASS');
