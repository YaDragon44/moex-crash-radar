// Investor Radar R1.8.30 — Issuer Risk Registry Hardening
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
  asOf:'2026-06-30',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'X5 H1 2026 IFRS financial results',sourceUrl:'https://www.x5.ru/ru/news/x5-obyavlyaet-o-roste-vyruchki-na-99-vo-2-kv-2026-g-rentabelnost-skorr-ebitda-do-primeneniya-msfo-ifrs-16-sostavila-60/',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,riskLevel:'MEDIUM',coverage:'RETAIL_GROWTH_MARGIN_LEVERAGE_PROFIT_RATING',items:['H1 2026 revenue 2,480,513 mn RUB, +10.5% y/y','H1 2026 adjusted EBITDA margin pre-IFRS 16: 5.7%','Net debt/EBITDA pre-IFRS 16 at 30 Jun 2026: 1.08x','H1 2026 net profit 34,482 mn RUB, -28.4% y/y','ACRA rating AAA(RU), stable, confirmed 24 Jun 2026','Expert RA rating ruAAA, stable, confirmed 29 Jul 2026','Model classification: MEDIUM because net profit declined y/y; thresholds are model assumptions, not rating-agency facts.'],ratingSources:['https://acra-ratings.ru/press-releases/7029/','https://raexpert.ru/releases/2026/jul29d']},
  sanctionsRegulatory:{verified:false,critical:false,items:['Separate primary-source sanctions/regulatory review required.']}
 },
 MOEX:{
  asOf:'2026-06-30',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'Moscow Exchange Q2 2026 IFRS results',sourceUrl:'https://www.moex.com/n103659',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,riskLevel:'LOW',coverage:'EXCHANGE_FEES_PROFIT_MARGIN_COSTS_LIQUIDITY_RATING',items:['Q2 2026 fee and commission income 22,271.7 mn RUB, +24.8% y/y','Q2 2026 net profit 15,766.2 mn RUB, +4.7% y/y','Q2 2026 adjusted EBITDA margin 67.6%','Q2 2026 total OPEX +10.4% y/y','Cash position at 30 Jun 2026: 194 bn RUB','Debt at 30 Jun 2026: 0','Expert RA reaffirmed ruAAA with stable outlook, disclosed in MOEX Q2 2026 results','Model classification: LOW financial issuer risk; thresholds are model assumptions. Sanctions/regulatory risk is assessed separately and remains material.']},
  sanctionsRegulatory:{verified:false,critical:true,items:['MOEX is subject to separate sanctions/regulatory review. Financial issuer-risk verification does not neutralize designation risk.']}
 },
 SBER:{
  asOf:'2025-12-31',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'MOEX issuer financials / Sber disclosure',sourceUrl:'https://www.moex.com/en/stocks/sber',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,riskLevel:'MEDIUM',coverage:'BANK_ROE_CAPITAL_ASSET_QUALITY',items:['ROE 2025: 22.7%','CET1 2025: 12.3%','NPL 2025: 4.9%','Cost of Risk 2025: 1.30%','Model classification: MEDIUM because NPL >= 4% and Cost of Risk >= 1%; thresholds are model assumptions, not regulatory facts.']},
  sanctionsRegulatory:{verified:false,critical:false,items:['Separate sanctions/regulatory registry is used; designation is material risk but not thesis destruction.']}
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
 return {ticker:String(t||'').toUpperCase(),sourceExists,riskVerified,status:r.riskStatus||'LOCK',reason:riskVerified?'issuer_risk_verified':sourceExists?'source_exists_risk_not_verified':'source_or_risk_missing'};
}
global.InvestorRadarIssuerRisk={REGISTRY,get,audit};if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
