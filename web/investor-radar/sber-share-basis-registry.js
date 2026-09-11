// Investor Radar R1.8.20 — SBER Share Basis Registry
// Primary-source issue sizes are verified, but issue size is NOT silently treated as shares outstanding.
(function(global){
'use strict';
const REGISTRY={
 ticker:'SBER',
 common:{
  ticker:'SBER',
  type:'COMMON',
  issueSize:21586948000,
  faceValueRub:3,
  isin:'RU0009029540',
  verified:true,
  source:'MOEX security profile',
  sourceUrl:'https://www.moex.com/en/stocks/sber',
  asOf:'2026-09-11'
 },
 preferred:{
  ticker:'SBERP',
  type:'PREFERRED',
  issueSize:1000000000,
  faceValueRub:3,
  isin:'RU0009029557',
  verified:true,
  source:'MOEX security profile',
  sourceUrl:'https://www.moex.com/en/stocks/sberp',
  asOf:'2026-09-11'
 },
 methodology:'MOEX issue size verifies issued securities only. BVPS/P/B stays blocked until shares outstanding / treasury-share treatment and attributable common equity are independently verified.'
};
function audit(input){
 const commonOk=REGISTRY.common.verified===true&&Number(REGISTRY.common.issueSize)>0&&REGISTRY.common.source&&REGISTRY.common.asOf;
 const preferredOk=REGISTRY.preferred.verified===true&&Number(REGISTRY.preferred.issueSize)>0&&REGISTRY.preferred.source&&REGISTRY.preferred.asOf;
 const outstandingVerified=input?.commonSharesOutstandingVerified===true&&Number.isFinite(Number(input?.commonSharesOutstanding))&&Number(input.commonSharesOutstanding)>0;
 const attributableEquityVerified=input?.attributableCommonEquityVerified===true&&Number.isFinite(Number(input?.attributableCommonEquityBnRub))&&Number(input.attributableCommonEquityBnRub)>0;
 const treasuryTreatmentVerified=input?.treasuryTreatmentVerified===true;
 const missing=[];
 if(!commonOk) missing.push('common_issue_size');
 if(!preferredOk) missing.push('preferred_issue_size');
 if(!outstandingVerified) missing.push('common_shares_outstanding');
 if(!treasuryTreatmentVerified) missing.push('treasury_share_treatment');
 if(!attributableEquityVerified) missing.push('attributable_common_equity');
 const verified=missing.length===0;
 return {
  status:verified?'VERIFIED':'PARTIAL',verified,missing,
  commonIssueSize:REGISTRY.common.issueSize,
  preferredIssueSize:REGISTRY.preferred.issueSize,
  totalIssuedShares:REGISTRY.common.issueSize+REGISTRY.preferred.issueSize,
  warning:'Issue size is not equivalent to verified shares outstanding; do not use it as BVPS denominator without treasury/outstanding confirmation.'
 };
}
global.InvestorRadarSberShareBasis={REGISTRY,audit};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberShareBasis;
})(typeof window!=='undefined'?window:globalThis);
