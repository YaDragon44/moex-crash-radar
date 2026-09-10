const assert=require('assert');
const I=require('./sber-valuation-runtime-integration.js');
const R=require('./sber-valuation-registry.js');
const F=require('./multiples-data-factory.js');
const U=require('./peer-universe-registry.js');
const E=require('./peer-earnings-registry.js');
const P=require('./peer-pe-data-factory.js');

const runtime={
 verified:true,status:'VERIFIED',asOf:'2026-09-10T20:00:00Z',
 historical:[
  {verified:true,year:2023,date:'2023-12-29',close:271.9,source:'MOEX ISS candles'},
  {verified:true,year:2024,date:'2024-12-30',close:279.56,source:'MOEX ISS candles'},
  {verified:true,year:2025,date:'2025-12-30',close:300.05,source:'MOEX ISS candles'}
 ],
 peers:{
  VTBR:{verified:true,ticker:'VTBR',price:92.5,updateTime:'2026-09-10',source:'MOEX ISS marketdata'},
  T:{verified:true,ticker:'T',price:3210,updateTime:'2026-09-10',source:'MOEX ISS marketdata'}
 }
};
const x=I.build({registry:R,runtime,multiplesFactory:F,peerUniverse:U,peerEarnings:E,peerPEFactory:P});
assert.equal(x.status,'VERIFIED');
assert.equal(x.verified,true);
assert.equal(x.historical.historicalPE.length,3);
assert.equal(x.peers.peerPE.length,2);
assert.equal(x.missing.length,0);
assert.ok(Math.abs(x.historical.historicalPE[0]-271.9/69.10)<1e-12);
assert.ok(Math.abs(x.peers.peerPE[0]-92.5/79.4)<1e-12);

const partial=I.build({registry:R,runtime:{...runtime,verified:false},multiplesFactory:F,peerUniverse:U,peerEarnings:E,peerPEFactory:P});
assert.equal(partial.status,'LOCK');
assert.ok(partial.missing.includes('moex_runtime_verified'));
console.log('R1.8.18 SBER valuation runtime integration tests: PASS');
