'use strict';
const assert=require('assert');
const Gate=require('./sber-issuer-report-extraction.js');

const current=Gate.current();
assert.equal(current.status,'PARTIAL');
assert.equal(current.verified,false);
assert(current.missing.includes('attributable_common_equity'));
assert(current.missing.includes('treasury_common_shares'));
assert(current.missing.includes('preferred_treatment'));
assert.equal(current.fields,null);

const src='https://www.e-disclosure.ru/portal/files.aspx?id=3043&type=5';
const ev=(locator,quoteOrField)=>({primary:true,sourceUrl:src,locator,quoteOrField});
const fixture=Gate.assess({
 documentHash:'sha256:test-fixture-only',extractedAt:'2026-09-12T15:00:00Z',
 fields:{
  attributableEquityToShareholdersRub:10000,
  attributableCommonEquityRub:9500,
  commonIssueSize:100,
  treasuryCommonShares:5,
  commonSharesOutstanding:95,
  preferredTreatmentVerified:true
 },
 evidence:{
  attributableEquityToShareholders:ev('fixture:p1','field A'),
  attributableCommonEquity:ev('fixture:p2','field B'),
  treasuryCommonShares:ev('fixture:p3','field C'),
  commonSharesOutstanding:ev('fixture:p4','field D'),
  preferredTreatment:ev('fixture:p5','field E')
 }
});
assert.equal(fixture.status,'VERIFIED');
assert.equal(fixture.verified,true);
assert.equal(fixture.fields.commonSharesOutstanding,95);

const bad=Gate.assess({
 documentHash:'sha256:test',extractedAt:'2026-09-12T15:00:00Z',
 fields:{attributableEquityToShareholdersRub:10000,attributableCommonEquityRub:9500,commonIssueSize:100,treasuryCommonShares:5,commonSharesOutstanding:96,preferredTreatmentVerified:true},
 evidence:{
  attributableEquityToShareholders:ev('p1','A'),attributableCommonEquity:ev('p2','B'),treasuryCommonShares:ev('p3','C'),commonSharesOutstanding:ev('p4','D'),preferredTreatment:ev('p5','E')
 }
});
assert.equal(bad.status,'PARTIAL');
assert(bad.missing.includes('share_reconciliation'));
assert.equal(bad.fields,null);

const untraceable=Gate.assess({
 documentHash:'sha256:test',extractedAt:'2026-09-12T15:00:00Z',
 fields:{attributableEquityToShareholdersRub:10000,attributableCommonEquityRub:9500,commonIssueSize:100,treasuryCommonShares:5,commonSharesOutstanding:95,preferredTreatmentVerified:true},
 evidence:{}
});
assert.equal(untraceable.status,'PARTIAL');
assert(untraceable.missing.includes('attributable_equity_to_shareholders'));

console.log('R1.8.40 SBER issuer report extraction gate: PASS');
