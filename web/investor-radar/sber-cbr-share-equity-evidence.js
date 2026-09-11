// Investor Radar R1.8.34 — SBER CBR Share / Equity Evidence
// Primary-source bridge from Bank of Russia form 0409810 to treasury-share treatment.
// IMPORTANT: statutory/regulatory equity is NOT common equity attributable and must not unlock common BVPS/P-B.
(function(global){
'use strict';
const EVIDENCE=Object.freeze({
 ticker:'SBER',
 asOf:'2025-12-31',
 source:'Bank of Russia form 0409810, Sberbank, as of 01.01.2026',
 sourceUrl:'https://cbr.ru/banking_sector/credit/coinfo/f810/1904/?dt=202601&regnum=1481',
 commonIssueSize:21586948000,
 preferredIssueSize:1000000000,
 treasuryOwnSharesBalanceReported:false,
 treasuryAcquisitionsReported:false,
 treasuryDisposalsReported:false,
 statutoryEquityThousandRub:8115080880,
 evidenceNotes:[
  'CBR form 0409810 shows no own shares in the treasury-shares column at year-end.',
  'CBR form 0409810 shows no treasury-share acquisitions or disposals during 2025.',
  'Year-end total sources of capital reported in the form: 8,115,080,880 thousand RUB.',
  'This capital figure is not treated as common equity attributable to ordinary shareholders.'
 ]
});

function assess(input={}){
 const issue=Number(input.commonIssueSize??EVIDENCE.commonIssueSize);
 const preferred=Number(input.preferredIssueSize??EVIDENCE.preferredIssueSize);
 const sourceOk=!!EVIDENCE.source&&!!EVIDENCE.sourceUrl&&!!EVIDENCE.asOf;
 const noTreasury=EVIDENCE.treasuryOwnSharesBalanceReported===false&&EVIDENCE.treasuryAcquisitionsReported===false&&EVIDENCE.treasuryDisposalsReported===false;
 const missing=[];
 if(!(Number.isFinite(issue)&&issue>0)) missing.push('common_issue_size');
 if(!(Number.isFinite(preferred)&&preferred>0)) missing.push('preferred_issue_size');
 if(!sourceOk) missing.push('source_metadata');
 if(!noTreasury) missing.push('treasury_share_evidence');
 if(missing.length) return {status:'PARTIAL',verified:false,missing,treasuryCommonShares:null,commonSharesOutstanding:null};
 const statutoryEquityRub=EVIDENCE.statutoryEquityThousandRub*1000;
 const totalIssuedShares=issue+preferred;
 return {
  status:'VERIFIED',verified:true,missing:[],
  treasuryTreatmentVerified:true,
  treasuryCommonShares:0,
  commonSharesOutstanding:issue,
  commonIssueSize:issue,
  preferredIssueSize:preferred,
  statutoryEquityRub,
  statutoryAllShareBvpsProxy:statutoryEquityRub/totalIssuedShares,
  proxyOnly:true,
  commonEquityAttributableVerified:false,
  preferredTreatmentVerified:false,
  source:EVIDENCE.source,sourceUrl:EVIDENCE.sourceUrl,asOf:EVIDENCE.asOf,
  interpretation:'No treasury shares are reported in the CBR year-end capital form; therefore common shares outstanding are reconciled to issued common shares for share-basis purposes. The statutory equity figure is only an all-share proxy and cannot unlock common BVPS/P-B without common-equity attribution and explicit preferred-share treatment.',
  rule:'Treasury/outstanding share basis may be VERIFIED while common-equity attribution remains PARTIAL.'
 };
}

global.InvestorRadarSberCbrShareEquityEvidence={EVIDENCE,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberCbrShareEquityEvidence;
})(typeof window!=='undefined'?window:globalThis);
