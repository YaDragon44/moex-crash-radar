// Investor Radar R1.8.39 — SBER Attributable Common Equity Acquisition Gate
// Purpose: acquire a primary-source basis for common BVPS/P/B without substituting regulatory capital,
// total equity/capital, issued share count, or historical preferred-share terms for current attributable common equity.
(function(global){
'use strict';

const EVIDENCE=Object.freeze({
 ticker:'SBER',
 issuerReport2025:{
  period:'2025-12M',
  published:'2026-03-30',
  source:'Interfax Corporate Disclosure Center — Sberbank issuer report archive',
  sourceUrl:'https://www.e-disclosure.ru/portal/files.aspx?id=3043&type=5',
  artifactType:'ZIP',
  artifactPublished:true,
  exactCommonEquityExtracted:false
 },
 dividendParity2025:{
  commonDividendRub:37.64,
  preferredDividendRub:37.64,
  source:'Interfax Corporate Disclosure Center — Sberbank 2025 dividend recommendation',
  sourceUrl:'https://www.e-disclosure.ru/portal/event.aspx?EventId=7tSumUE9bUa3nmDlDRhZaQ-B-B',
  note:'Equal 2025 dividends are current factual evidence for that distribution only; they do not prove liquidation/equity attribution parity.'
 },
 forbiddenSubstitutions:[
  'MOEX Equity (Capital) -> attributable common equity',
  'CBR regulatory capital -> attributable common equity',
  'issued common shares -> shares outstanding',
  'historical SBERP charter terms -> current preferred treatment',
  'equal annual dividend -> equal liquidation/equity attribution rights'
 ]
});

function positive(x){ return Number.isFinite(Number(x)) && Number(x)>0; }
function nonNegative(x){ return Number.isFinite(Number(x)) && Number(x)>=0; }

function assess(input={}){
 const primary= input.primarySourceVerified===true && !!input.primarySourceUrl;
 const attributable= primary && positive(input.attributableEquityToShareholdersRub);
 const commonAllocation= primary && input.commonAllocationMethodVerified===true && positive(input.attributableCommonEquityRub);
 const commonIssued= positive(input.commonIssueSize);
 const treasuryKnown= primary && nonNegative(input.treasuryCommonShares);
 const outstanding= primary && positive(input.commonSharesOutstanding);
 const reconcile= commonIssued && treasuryKnown && outstanding && Number(input.commonIssueSize)-Number(input.treasuryCommonShares)===Number(input.commonSharesOutstanding);
 const preferred= primary && input.preferredTreatmentVerified===true && !!input.preferredTreatmentSourceUrl;
 const period= !!input.asOf;
 const missing=[];
 if(!primary) missing.push('primary_source');
 if(!attributable) missing.push('attributable_equity_to_shareholders');
 if(!commonAllocation) missing.push('attributable_common_equity');
 if(!treasuryKnown) missing.push('treasury_common_shares');
 if(!outstanding) missing.push('common_shares_outstanding');
 if(!reconcile) missing.push('share_reconciliation');
 if(!preferred) missing.push('preferred_treatment');
 if(!period) missing.push('as_of');
 const verified=missing.length===0;
 const bvps=verified?Number(input.attributableCommonEquityRub)/Number(input.commonSharesOutstanding):null;
 return {
  status:verified?'VERIFIED':'PARTIAL',verified,missing,
  attributableEquityToShareholdersRub:attributable?Number(input.attributableEquityToShareholdersRub):null,
  attributableCommonEquityRub:commonAllocation?Number(input.attributableCommonEquityRub):null,
  commonSharesOutstanding:outstanding?Number(input.commonSharesOutstanding):null,
  treasuryCommonShares:treasuryKnown?Number(input.treasuryCommonShares):null,
  bvps,
  source:primary?{url:input.primarySourceUrl,asOf:input.asOf}:null,
  preferredTreatment:preferred?{verified:true,sourceUrl:input.preferredTreatmentSourceUrl}:null,
  evidence:EVIDENCE,
  message:verified?'Primary-source attributable common equity basis verified; common BVPS may be used by the bank valuation gate.':'Недостаточно данных для обоснованного расчёта common BVPS/P/B Сбербанка.',
  rule:'Fail closed. A current primary source must independently establish attributable shareholder equity, common allocation, treasury/outstanding common-share basis, and preferred-share treatment.'
 };
}

function unresolved(){
 return assess({
  primarySourceVerified:false,
  commonIssueSize:21586948000,
  asOf:'2026-09-12'
 });
}

global.InvestorRadarSberAttributableCommonEquity={EVIDENCE,assess,unresolved};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberAttributableCommonEquity;
})(typeof window!=='undefined'?window:globalThis);
