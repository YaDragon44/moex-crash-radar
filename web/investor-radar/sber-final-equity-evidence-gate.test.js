const assert=require('assert');
const G=require('./sber-final-equity-evidence-gate.js');

let r=G.assess();
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert.equal(r.commonSharesOutstanding,21586948000);
assert.equal(r.attributableCommonEquityRub,null);
assert.equal(r.commonBvps,null);
for(const k of ['current_charter_preferred_rights','preferred_liquidation_priority','equity_allocation_method','attributable_common_equity','primary_equity_source']) assert(r.missing.includes(k),k);
assert.equal(G.BASE.statutoryCapitalIsCommonEquity,false);
assert.equal(G.BASE.moexTotalEquityIsCommonEquity,false);

r=G.assess({
 currentCharterRightsVerified:true,
 preferredLiquidationRuleVerified:true,
 equityAllocationMethodVerified:true,
 attributableCommonEquityVerified:true,
 attributableCommonEquityRub:8000000000000,
 primaryEquitySourceVerified:true,
 primaryEquitySourceUrl:'https://example.invalid/primary'
});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.missing.length,0);
assert(Math.abs(r.commonBvps-(8000000000000/21586948000))<1e-12);
console.log('R1.8.37 final SBER equity evidence gate: PASS');
