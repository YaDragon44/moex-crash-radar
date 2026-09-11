// Investor Radar R1.8.21 — SBER Attributable Equity & Treasury Shares Gate
// No BVPS/P-B verification until attributable equity, treasury-share treatment and shares outstanding are primary-source verified.
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
 if(missing.length) return {status:'PARTIAL',verified:false,missing,commonSharesOutstanding:null,attributableCommonEquityRub:null,reconciled:false};
 return {
  status:'VERIFIED',verified:true,missing:[],commonIssueSize:issued,treasuryCommonShares:treasury,
  commonSharesOutstanding:outstanding,attributableCommonEquityRub:attributable,reconciled:true,
  equitySource:input.equitySource,shareSource:input.shareSource,treasurySource:input.treasurySource,asOf:input.asOf,
  method:'Common shares outstanding = issued common shares - verified treasury common shares; attributable common equity must be independently sourced; preferred-share treatment must be explicit.'
 };
}

function unresolved(){
 return {status:'PARTIAL',verified:false,missing:['treasury_common_shares','common_shares_outstanding','attributable_common_equity','preferred_share_treatment'],reason:'MOEX issuer page confirms total capital and issue sizes but does not provide enough current detail to verify common BVPS basis.'};
}

global.InvestorRadarSberEquityAttribution={assess,unresolved};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberEquityAttribution;
})(typeof window!=='undefined'?window:globalThis);
