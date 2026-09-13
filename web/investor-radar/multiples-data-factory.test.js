const assert=require('assert');
const F=require('./multiples-data-factory.js');
const candles=[
 {date:'2022-12-29',close:100},{date:'2023-12-29',close:120},{date:'2024-12-30',close:150},{date:'2024-12-31',close:155}
];
let h=F.historicalPE({candles,epsSeries:[{year:2022,eps:10,verified:true,source:'Issuer FY2022'},{year:2023,eps:12,verified:true,source:'Issuer FY2023'},{year:2024,eps:15.5,verified:true,source:'Issuer FY2024'}],priceSource:'MOEX ISS'});
assert.equal(h.verified,true);assert.equal(h.points.length,3);assert.equal(h.points[2].date,'2024-12-31');assert(Math.abs(h.points[2].pe-10)<1e-12);
h=F.historicalPE({candles,epsSeries:[{year:2022,eps:10,verified:false,source:'x'},{year:2023,eps:12,verified:true,source:'y'}],priceSource:'MOEX ISS'});assert.equal(h.verified,false);assert(h.missing.includes('eps_2022_unverified'));
let p=F.peerPE({peers:[{ticker:'A',price:100,eps:10,verified:true,priceSource:'MOEX',epsSource:'A IFRS',asOf:'2026-09-10'},{ticker:'B',price:90,eps:9,verified:true,priceSource:'MOEX',epsSource:'B IFRS',asOf:'2026-09-10'}]});assert.equal(p.verified,true);assert.deepEqual(p.peerPE,[10,10]);
p=F.peerPE({peers:[{ticker:'A',price:100,eps:10,verified:false,priceSource:'MOEX',epsSource:'A IFRS',asOf:'2026-09-10'}]});assert.equal(p.verified,false);assert.equal(p.points.length,0);
let b=F.build({candles,epsSeries:[{year:2022,eps:10,verified:true,source:'Issuer FY2022'},{year:2023,eps:12,verified:true,source:'Issuer FY2023'},{year:2024,eps:15.5,verified:true,source:'Issuer FY2024'}],priceSource:'MOEX ISS',peers:[{ticker:'A',price:100,eps:10,verified:true,priceSource:'MOEX',epsSource:'A IFRS',asOf:'2026-09-10'},{ticker:'B',price:90,eps:9,verified:true,priceSource:'MOEX',epsSource:'B IFRS',asOf:'2026-09-10'}],asOf:'2026-09-10'});assert.equal(b.verified,true);assert.equal(b.historicalPE.length,3);assert.equal(b.peerPE.length,2);
console.log('R1.8.9 multiples data factory tests: PASS');
