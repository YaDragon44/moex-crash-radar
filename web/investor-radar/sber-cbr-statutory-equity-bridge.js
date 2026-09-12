// Investor Radar R1.8.42 — SBER CBR Statutory Equity Bridge / Scope Boundary Gate
// Captures verified Bank of Russia form 0409810 evidence while preventing misuse as common BVPS/P/B input.
(function(global){
'use strict';

const EVIDENCE=Object.freeze({
 ticker:'SBER',
 issuer:'ПАО Сбербанк России',
 reportDate:'2026-01-01',
 reportingPeriod:'2025',
 form:'0409810',
 source:'Банк России — Отчет об изменениях в капитале кредитной организации (публикуемая форма)',
 sourceUrl:'https://cbr.ru/banking_sector/credit/coinfo/f810/1904/?dt=202601&regnum=1481',
 asOf:'2026-09-12',
 values:{
  charterCapitalThousandRub:67760844,
  totalCapitalSourcesThousandRub:8115080880,
  retainedEarningsThousandRub:7952829520,
  ordinaryDividendsDeclaredThousandRub:752089268,
  preferredDividendsDeclaredThousandRub:34840000,
  ownSharesBalanceReported:'NONE_REPORTED',
  ownSharesAcquisitionsReported:'NONE_REPORTED',
  ownSharesDisposalsReported:'NONE_REPORTED'
 },
 locators:{
  formHeader:'CBR 0409810, lines 36-53',
  ownSharesActivity:'rows 19.1-19.2, CBR page lines 87-89',
  dividendSplit:'rows 21.1-21.2, CBR page lines 91-93',
  closingCapital:'row 24, CBR page line 96'
 }
});

const BOUNDARIES=Object.freeze([
 'CBR statutory bank-level capital sources are not IFRS consolidated equity attributable to shareholders.',
 'A blank monetary own-shares column is not a verified exact treasury common-share count.',
 'Standalone bank reporting is not automatically equivalent to consolidated group reporting.',
 'Declared dividend allocation between common and preferred shares does not establish liquidation or capital-allocation rights.'
]);

function assess(input={}){
 const e=input.evidence||EVIDENCE;
 const primary=!!e&&e.form==='0409810'&&/^https:\/\/cbr\.ru\//.test(e.sourceUrl||'')&&e.reportDate==='2026-01-01';
 const values=e?.values||{};
 const numbersOk=[values.charterCapitalThousandRub,values.totalCapitalSourcesThousandRub,values.retainedEarningsThousandRub,values.ordinaryDividendsDeclaredThousandRub,values.preferredDividendsDeclaredThousandRub].every(v=>Number.isFinite(Number(v))&&Number(v)>=0);
 const ownSharesDisclosure=values.ownSharesBalanceReported==='NONE_REPORTED'&&values.ownSharesAcquisitionsReported==='NONE_REPORTED'&&values.ownSharesDisposalsReported==='NONE_REPORTED';
 const evidenceVerified=primary&&numbersOk&&ownSharesDisclosure;
 const forbiddenUnlock=input.treasuryCommonSharesAssumption!==undefined||input.useStatutoryCapitalAsCommonEquity===true;
 return {
  ticker:'SBER',
  status:evidenceVerified?'VERIFIED_EVIDENCE':'PARTIAL',
  evidenceVerified,
  commonBvpsEligible:false,
  valuationStatus:'PARTIAL',
  blockers:[
   'ifrs_consolidated_attributable_shareholder_equity',
   'common_vs_preferred_equity_allocation',
   'exact_consolidated_treasury_common_shares',
   'common_shares_outstanding',
   'current_preferred_capital_rights'
  ],
  evidence:e,
  scopeBoundaries:BOUNDARIES,
  forbiddenUnlockDetected:forbiddenUnlock,
  message:'CBR 0409810 evidence is valid for statutory bank-level capital disclosure, but insufficient for common BVPS/P/B.',
  rule:'Fail closed: never convert blank own-share disclosure to treasuryCommonShares=0 and never substitute statutory capital sources for attributable common equity.'
 };
}

function current(){return assess({evidence:EVIDENCE});}

global.InvestorRadarSberCbrStatutoryEquityBridge={EVIDENCE,BOUNDARIES,assess,current};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberCbrStatutoryEquityBridge;
})(typeof window!=='undefined'?window:globalThis);
