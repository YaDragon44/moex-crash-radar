'use strict';
const assert=require('assert');
const G=require('./sber-cbr-statutory-equity-bridge.js');

let r=G.current();
assert.equal(r.status,'VERIFIED_EVIDENCE');
assert.equal(r.evidenceVerified,true);
assert.equal(r.commonBvpsEligible,false);
assert.equal(r.valuationStatus,'PARTIAL');
assert(r.blockers.includes('ifrs_consolidated_attributable_shareholder_equity'));
assert(r.blockers.includes('exact_consolidated_treasury_common_shares'));
assert.equal(r.evidence.values.totalCapitalSourcesThousandRub,8115080880);
assert.equal(r.evidence.values.ownSharesBalanceReported,'NONE_REPORTED');

r=G.assess({evidence:G.EVIDENCE,treasuryCommonSharesAssumption:0});
assert.equal(r.evidenceVerified,true);
assert.equal(r.forbiddenUnlockDetected,true);
assert.equal(r.commonBvpsEligible,false);

r=G.assess({evidence:G.EVIDENCE,useStatutoryCapitalAsCommonEquity:true});
assert.equal(r.forbiddenUnlockDetected,true);
assert.equal(r.commonBvpsEligible,false);

const bad=JSON.parse(JSON.stringify(G.EVIDENCE));
bad.sourceUrl='https://example.com/not-primary';
r=G.assess({evidence:bad});
assert.equal(r.status,'PARTIAL');
assert.equal(r.evidenceVerified,false);
assert.equal(r.commonBvpsEligible,false);

console.log('R1.8.42 SBER CBR statutory equity bridge: PASS');
