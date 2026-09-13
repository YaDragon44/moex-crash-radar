'use strict';
const assert=require('assert');
const A=require('./sber-valuation-blocker-reaudit.js');
const V={status:'VERIFIED',verified:true};
let r=A.audit({peRuntime:{...V,historical:{points:[1,2,3]},peers:{points:[1,2]}},pbRuntime:{...V,pb:0.73},bankQuality:V,reportedBvps:V,currentPrice:283.32,priceVerified:true});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.deepEqual(r.blockers,[]);
assert.equal(r.peerCount,2);
assert.equal(r.historicalPeCount,3);
assert.equal(r.pb,0.73);
assert.equal(r.denominatorSource,'SBER_ANNUAL_REPORT_2025_NET_ASSETS_PER_COMMON_SHARE');

r=A.audit({peRuntime:{status:'PARTIAL',verified:false},pbRuntime:{...V,pb:0.73},bankQuality:V,reportedBvps:V,currentPrice:283.32,priceVerified:true});
assert.equal(r.status,'PARTIAL');
assert(r.blockers.includes('pe_runtime'));
assert.equal(r.message,'Недостаточно данных для обоснованного вывода');

r=A.audit({peRuntime:V,pbRuntime:V,bankQuality:V,reportedBvps:V,currentPrice:null,priceVerified:false});
assert(r.blockers.includes('current_price'));
console.log('R1.8.46 SBER valuation blocker re-audit tests: PASS');
