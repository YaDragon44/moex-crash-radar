const assert=require('assert');
const M=require('./multiples-registry.js');
for(const t of ['SBER','YDEX','X5','MOEX']){const x=M.get(t);assert.equal(x.status,'LOCK');assert.equal(M.isVerified(x),false);assert(Array.isArray(x.historicalPE));assert(Array.isArray(x.peerPE));}
assert.equal(M.get('UNKNOWN').status,'LOCK');
assert.equal(M.isVerified({status:'VERIFIED',historicalPE:[5,6,7],peerPE:[8,9],source:'src',asOf:'2026-09-10'}),true);
assert.equal(M.isVerified({status:'VERIFIED',historicalPE:[5,6],peerPE:[8,9],source:'src',asOf:'2026-09-10'}),false);
console.log('R1.8.8 multiples registry tests: PASS');
