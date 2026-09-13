// Investor Radar R1.8.41 — SBER Primary Document Locator Gate
// Confirms exact primary document endpoints before any field extraction.
(function(global){
'use strict';

const DOCUMENTS=Object.freeze({
 annualReport2025:{
  type:'ANNUAL_REPORT_2025',
  period:'2025',
  primary:true,
  source:'Sberbank official annual report PDF',
  url:'https://www.sberbank.com/common/img/uploaded/_new_site/com/gosa2026/sber-ar-2025-ru.pdf',
  discoveredVia:'RAEX annual-report registry link to sberbank.com',
  fetchStatus:'UPSTREAM_502_FROM_CURRENT_ENVIRONMENT',
  extractionReady:false
 },
 interactiveAnnualReport2025:{
  type:'INTERACTIVE_ANNUAL_REPORT_2025',
  period:'2025',
  primary:true,
  source:'Sberbank shareholder interactive annual report',
  url:'https://shareholder.sberbank.com/AR25/',
  discoveredVia:'RAEX annual-report registry link to shareholder.sberbank.com',
  fetchStatus:'UPSTREAM_502_FROM_CURRENT_ENVIRONMENT',
  extractionReady:false
 },
 issuerReport2025:{
  type:'ISSUER_REPORT_2025_12M',
  period:'2025-12M',
  primary:true,
  source:'Interfax Corporate Disclosure Center — Sberbank issuer report archive',
  url:'https://www.e-disclosure.ru/portal/files.aspx?id=3043&type=5',
  published:'2026-03-30',
  artifact:'ZIP 1.16 MB',
  listingConfirmed:true,
  extractionReady:false
 }
});

const REQUIRED_TARGETS=Object.freeze([
 'attributable_equity_to_shareholders',
 'attributable_common_equity',
 'treasury_common_shares',
 'common_shares_outstanding',
 'preferred_share_current_rights'
]);

function assess(input={}){
 const docs=input.documents||DOCUMENTS;
 const annual=docs.annualReport2025;
 const issuer=docs.issuerReport2025;
 const urlsVerified=!!annual?.primary&&/^https:\/\/www\.sberbank\.com\//.test(annual.url||'')&&!!issuer?.primary&&/^https:\/\/www\.e-disclosure\.ru\//.test(issuer.url||'');
 const extracted=input.extracted===true;
 const targetEvidence=input.targetEvidence||{};
 const missing=[];
 if(!urlsVerified) missing.push('primary_document_urls');
 if(!extracted) missing.push('document_content_extraction');
 for(const t of REQUIRED_TARGETS){
  const e=targetEvidence[t];
  if(!(e&&e.primary===true&&e.locator&&e.sourceUrl&&e.value!==undefined)) missing.push(t);
 }
 const verified=missing.length===0;
 return {
  status:verified?'VERIFIED':'PARTIAL',verified,missing:[...new Set(missing)],
  documents:docs,
  targets:REQUIRED_TARGETS,
  message:verified?'Primary documents and all target fields are located with traceable evidence.':'Недостаточно данных для обоснованного расчёта common BVPS/P/B Сбербанка.',
  rule:'Document discovery alone is not evidence extraction. R1.8 valuation stays blocked until exact primary-source fields are located and captured.'
 };
}

function current(){return assess({documents:DOCUMENTS,extracted:false,targetEvidence:{}});}

global.InvestorRadarSberPrimaryDocumentLocator={DOCUMENTS,REQUIRED_TARGETS,assess,current};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberPrimaryDocumentLocator;
})(typeof window!=='undefined'?window:globalThis);
