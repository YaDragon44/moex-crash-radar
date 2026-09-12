const assert=require('assert');
const F=require('./peer-pe-data-factory.js');
const U={status:'APPROVED_UNIVERSE',peers:['AAA','BBB','CCC']};
const E={get:t=>({
 AAA:{verified:true,comparable:true,eps:10,source:'Issuer A',asOf:'2025-12-31'},
 BBB:{verified:true,comparable:true,eps:20,source:'Issuer B',asOf:'2025-12-31'},
 CCC:{verified:true,comparable:true,eps:-1,source:'Issuer C',asOf:'2025-12-31'}
}[t])};
let r=F.build(U,E,{AAA:{price:100,source:'MOEX',asOf:'2026-09-10'},BBB:{price:300,source:'MOEX',asOf:'2026-09-10'},CCC:{price:50,source:'MOEX',asOf:'2026-09-10'}});
assert.equal(r.verified,true);assert.deepEqual(r.peerPE,[10,15]);assert.equal(r.excluded.length,1);assert.equal(r.excluded[0].ticker,'CCC');
r=F.build({status:'LIMITED_UNIVERSE',peers:[]},E,{});assert.equal(r.status,'LOCK');assert.equal(r.verified,false);
r=F.build(U,E,{AAA:{price:100,source:'MOEX',asOf:'2026-09-10'}});assert.equal(r.verified,false);assert(r.missing.includes('peer_pe_2plus'));
const splitE={get:t=>t==='AAA'?{verified:true,comparable:true,eps:10,source:'Issuer A',asOf:'2025-12-31',corporateAction:{verified:false,ratioOld:1,ratioNew:10,effectiveDate:'2026-04-17',sourceUrl:'x'}}:E.get(t)};
r=F.build(U,splitE,{AAA:{price:100,source:'MOEX',asOf:'2026-09-10'},BBB:{price:300,source:'MOEX',asOf:'2026-09-10'}});
assert.equal(r.verified,false);assert(r.excluded.some(x=>x.ticker==='AAA'));
console.log('R1.8.46 peer P/E factory tests: PASS');
