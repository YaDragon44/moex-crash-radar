// Investor Radar R1.8.40 — SBER Issuer Report Extraction Gate
// Converts extracted primary-source evidence into a strict, auditable input set for common BVPS/P/B.
// It never infers missing equity/share-class facts from total capital, issue size or dividend parity.
(function(global){
'use strict';

const REPORT=Object.freeze({
 ticker:'SBER',
 period:'2025-12M',
 published:'2026-03-30',
 source:'Interfax Corporate Disclosure Center — PAO Sberbank issuer report',
 sourceUrl:'https://www.e-disclosure.ru/portal/files.aspx?id=3043&type=5',
 artifactType:'ZIP',
 artifactSizeMb:1.16,
 artifactConfirmed:true,
 extractionStatus:'ARTIFACT_CONFIRMED_CONTENT_NOT_EXTRACTED',
 asOf:'2026-09-12'
});

const REQUIRED=Object.freeze([
 'attributable_equity_to_shareholders',
 'attributable_common_equity',
 'treasury_common_shares',
 'common_shares_outstanding',
 'preferred_treatment'
]);

function positive(v){return Number.isFinite(Number(v))&&Number(v)>0;}
function nonNegative(v){return Number.isFinite(Number(v))&&Number(v)>=0;}
function evidenceOk(e){return !!e&&e.primary===true&&!!e.sourceUrl&&!!e.locator&&!!e.quoteOrField;}

function assess(extracted={}){
 const fields=extracted.fields||{};
 const evidence=extracted.evidence||{};
 const missing=[];
 if(!evidenceOk(evidence.attributableEquityToShareholders)||!positive(fields.attributableEquityToShareholdersRub)) missing.push(REQUIRED[0]);
 if(!evidenceOk(evidence.attributableCommonEquity)||!positive(fields.attributableCommonEquityRub)) missing.push(REQUIRED[1]);
 if(!evidenceOk(evidence.treasuryCommonShares)||!nonNegative(fields.treasuryCommonShares)) missing.push(REQUIRED[2]);
 if(!evidenceOk(evidence.commonSharesOutstanding)||!positive(fields.commonSharesOutstanding)) missing.push(REQUIRED[3]);
 if(!evidenceOk(evidence.preferredTreatment)||fields.preferredTreatmentVerified!==true) missing.push(REQUIRED[4]);
 const issued=Number(fields.commonIssueSize);
 const treasury=Number(fields.treasuryCommonShares);
 const outstanding=Number(fields.commonSharesOutstanding);
 const reconcile=positive(issued)&&nonNegative(treasury)&&positive(outstanding)&&issued-treasury===outstanding;
 if(!reconcile) missing.push('share_reconciliation');
 if(!extracted.documentHash) missing.push('document_hash');
 if(!extracted.extractedAt) missing.push('extracted_at');
 const verified=missing.length===0;
 return {
  status:verified?'VERIFIED':'PARTIAL',verified,missing:[...new Set(missing)],
  report:REPORT,
  fields:verified?{
   attributableEquityToShareholdersRub:Number(fields.attributableEquityToShareholdersRub),
   attributableCommonEquityRub:Number(fields.attributableCommonEquityRub),
   commonIssueSize:issued,
   treasuryCommonShares:treasury,
   commonSharesOutstanding:outstanding,
   preferredTreatmentVerified:true
  }:null,
  evidence:verified?evidence:null,
  documentHash:extracted.documentHash||null,
  extractedAt:extracted.extractedAt||null,
  message:verified?'Issuer-report evidence set is complete and internally reconciled.':'Недостаточно данных для обоснованного расчёта common BVPS/P/B Сбербанка.',
  rule:'Fail closed: every required field needs a primary-source locator and extracted field/quote; no substitution from total capital, issue size or dividend parity.'
 };
}

function current(){return assess({});}

global.InvestorRadarSberIssuerReportExtraction={REPORT,REQUIRED,assess,current};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberIssuerReportExtraction;
})(typeof window!=='undefined'?window:globalThis);
