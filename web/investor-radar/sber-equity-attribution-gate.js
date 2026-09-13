// Investor Radar R1.8.34 — SBER Attributable Equity & Treasury Shares Gate
// Treasury/outstanding share basis can be verified from CBR 0409810 evidence,
// but common BVPS/P-B remains blocked until common-equity attribution and preferred-share treatment are primary-source verified.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
const positive=x=>finite(x)&&Number(x)>0;

function assess(input){
 const missing=[];
 const issued=Number(input?.commonIssueSize);
 const treasury=Number(input?.treasuryCommonShares);
 const outstanding=Number(input?.commonSharesOutstanding);
 const attributable=Number(input?.attributableCommonEquityRub);
 if(input?.verified!==true) missing.push('verified_inputs');
 if(!positive(issued)) missing.push('common_issue_size');
 if(!finite(treasury)||treasury<0) missing.push('treasury_common_shares');
 if(!positive(outstanding)) missing.push('common_shares_outstanding');
 if(!positive(attributable)) missing.push('attributable_common_equity');
 if(input?.preferredTreatmentVerified!==true) missing.push('preferred_share_treatment');
 if(!input?.equitySource||!input?.shareSource||!input?.treasurySource||!input?.asOf) missing.push('source_metadata');
 if(!missing.length && issued-treasury!==outstanding) missing.push('share_reconciliation');
 const reconciled=positive(issued)&&finite(treasury)&&treasury>=0&&positive(outstanding)&&issued-treasury===outstanding;
 if(missing.length) return {status:'PARTIAL',verified:false,missing,commonSharesOutstanding:positive(outstanding)?outstanding:null,treasuryCommonShares:finite(treasury)&&treasury>=0?treasury:null,attributableCommonEquityRub:null,reconciled};
 return {
  status:'VERIFIED',verified:true,missing:[],commonIssueSize:issued,treasuryCommonShares:treasury,
  commonSharesOutstanding:outstanding,attributableCommonEquityRub:attributable,reconciled:true,
  equitySource:input.equitySource,shareSource:input.shareSource,treasurySource:input.treasurySource,asOf:input.asOf,
  method:'Common shares outstanding = issued common shares - verified treasury common shares; attributable common equity must be independently sourced; preferred-share treatment must be explicit.'
 };
}

function fromCbrEvidence(evidence,extra={}){
 const e=evidence||{};
 const shareBasisVerified=e.verified===true&&e.treasuryTreatmentVerified===true&&positive(e.commonIssueSize)&&finite(e.treasuryCommonShares)&&e.treasuryCommonShares>=0&&positive(e.commonSharesOutstanding)&&Number(e.commonIssueSize)-Number(e.treasuryCommonShares)===Number(e.commonSharesOutstanding);
 const missing=[];
 if(!shareBasisVerified) missing.push('treasury_or_outstanding_share_basis');
 if(!positive(extra.attributableCommonEquityRub)) missing.push('attributable_common_equity');
 if(extra.preferredTreatmentVerified!==true) missing.push('preferred_share_treatment');
 const verified=missing.length===0;
 return {
  status:verified?'VERIFIED':'PARTIAL',verified,missing,
  commonIssueSize:shareBasisVerified?Number(e.commonIssueSize):null,
  treasuryCommonShares:shareBasisVerified?Number(e.treasuryCommonShares):null,
  commonSharesOutstanding:shareBasisVerified?Number(e.commonSharesOutstanding):null,
  attributableCommonEquityRub:verified?Number(extra.attributableCommonEquityRub):null,
  preferredTreatmentVerified:extra.preferredTreatmentVerified===true,
  reconciled:shareBasisVerified,
  shareSource:shareBasisVerified?e.source:null,
  treasurySource:shareBasisVerified?e.source:null,
  equitySource:extra.equitySource||null,
  asOf:e.asOf||extra.asOf||null,
  reason:verified?'all_common_equity_basis_verified':'CBR evidence resolves treasury/outstanding shares only; common-equity attribution and preferred-share treatment remain required for common BVPS/P-B.'
 };
}

function unresolved(){
 return {status:'PARTIAL',verified:false,missing:['attributable_common_equity','preferred_share_treatment'],reason:'R1.8.34 CBR year-end evidence resolves treasury/outstanding share basis. Full common BVPS remains blocked because attributable common equity and preferred-share treatment are not yet independently verified.'};
}

global.InvestorRadarSberEquityAttribution={assess,fromCbrEvidence,unresolved};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberEquityAttribution;
})(typeof window!=='undefined'?window:globalThis);
