const assert=require('assert');
const G=require('./sber-current-charter-rights-gate.js');

let r=G.assess();
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert.equal(r.currentCharterRevision.approved,'2025-07-25');
assert.equal(r.currentCharterRevision.registered,'2025-07-28');
assert.equal(r.historicalRights.liquidationValueRub,1000);
assert.equal(r.historicalRights.historicalOnly,true);
assert.equal(r.currentDividendParity.commonDividendRub,37.64);
assert.equal(r.currentDividendParity.preferredDividendRub,37.64);
for(const k of ['current_charter_text','current_liquidation_right','current_dividend_right','current_voting_right','current_equity_priority']) assert(r.missing.includes(k),k);

r=G.assess({
 currentCharterTextVerified:true,
 currentCharterTextSourceUrl:'https://example.invalid/current-charter',
 currentLiquidationValueVerified:true,
 currentLiquidationValueRub:1000,
 currentDividendRightsVerified:true,
 currentVotingRightsVerified:true,
 currentEquityPriorityVerified:true
});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.missing.length,0);
assert.equal(r.currentRights.liquidationValueRub,1000);
console.log('R1.8.38 current SBER charter rights gate: PASS');
