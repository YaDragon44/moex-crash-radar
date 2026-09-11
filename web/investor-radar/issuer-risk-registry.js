// Investor Radar R1.8.25 — Issuer Risk Registry Hardening
// SOURCE_EXISTS != RISK_VERIFIED. Primary-source presence never unlocks issuer risk by itself.
(function(global){'use strict';
const lock=(items=[])=>({status:'LOCK',verified:false,critical:false,thesisBroken:false,coverage:'SOURCE_ONLY',items});
const REGISTRY={
 YDEX:{
  asOf:'2025-12-31',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'Yandex IR FY2025',sourceUrl:'https://ir.yandex.ru/financial-releases?report=q4&year=2025',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,coverage:'DEBT_LIQUIDITY_PROFITABILITY',items:['FY2025 revenue 1,441.1 bn RUB','Adjusted EBITDA 280.8 bn RUB','Cash + equivalents + short-term deposits 250.2 bn RUB','Adjusted net debt / adjusted EBITDA 0.2x']},
  sanctionsRegulatory:{verified:false,critical:false,items:['Separate primary-source sanctions/regulatory review required.']}
 },
 X5:{
  asOf:'2026-06-30',sourceStatus:'SOURCE_EXISTS',riskStatus:'LOCK',
  source:'X5 official financial statements/results',sourceUrl:'https://www.x5.ru/ru/investors/financial-statements/',
  issuer:lock(['Official FY2025 audited IFRS statements published 20 Mar 2026','Official H1 2026 IFRS statements published 13 Aug 2026','Source availability is confirmed, but issuer-risk metrics and thresholds are not yet fully verified.']),
  sanctionsRegulatory:{verified:false,critical:false,items:['Separate primary-source sanctions/regulatory review required.']}
 },
 MOEX:{
  asOf:'2026-06-30',sourceStatus:'SOURCE_EXISTS',riskStatus:'LOCK',
  source:'Moscow Exchange official IFRS/Annual Report',sourceUrl:'https://www.moex.com/s1355',
  issuer:lock(['FY2025 IFRS statements published 5 Mar 2026','H1 2026 interim IFRS statements published 26 Aug 2026','Source availability is confirmed, but sector-specific issuer-risk metrics are not yet fully verified.']),
  sanctionsRegulatory:{verified:false,critical:false,items:['Separate primary-source sanctions/regulatory review required.']}
 },
 SBER:{
  asOf:null,sourceStatus:'PARTIAL',riskStatus:'LOCK',source:null,sourceUrl:null,
  issuer:lock(['Bank-specific valuation/quality modules exist, but issuer-risk registry is not yet independently verified for full risk-gate use.']),
  sanctionsRegulatory:{verified:false,critical:false,items:['Separate primary-source sanctions/regulatory review required.']}
 }
};
function get(t){
 const k=String(t||'').toUpperCase();
 return REGISTRY[k]||{sourceStatus:'MISSING',riskStatus:'LOCK',issuer:lock(['Issuer absent from verified registry.']),sanctionsRegulatory:{verified:false,critical:false,items:['Sanctions/regulatory review absent.']}};
}
function audit(t){
 const r=get(t),i=r.issuer||{};
 const sourceExists=r.sourceStatus==='SOURCE_EXISTS'&&!!r.source&&!!r.sourceUrl;
 const riskVerified=r.riskStatus==='VERIFIED'&&i.status==='VERIFIED'&&i.verified===true;
 return {ticker:String(t||'').toUpperCase(),sourceExists,riskVerified,status:riskStatus||'LOCK',reason:riskVerified?'issuer_risk_verified':sourceExists?'source_exists_risk_not_verified':'source_or_risk_missing'};
}
global.InvestorRadarIssuerRisk={REGISTRY,get,audit};if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
