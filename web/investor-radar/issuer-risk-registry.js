// Investor Radar R1.8.33 — Issuer Risk Registry Sector Gate Coverage Audit
// SOURCE_EXISTS != RISK_VERIFIED. Every VERIFIED issuer-risk row must be derived from an explicit sector-specific gate.
// Sanctions/regulatory semantics are delegated to sanctions-regulatory-registry.js and never use legacy `critical` here.
(function(global){'use strict';
const lock=(items=[])=>({status:'LOCK',verified:false,critical:false,thesisBroken:false,coverage:'SOURCE_ONLY',items});
const delegatedSanctions=(items=[])=>({verified:false,status:'DELEGATED',material:null,designated:null,items});
const GATE_BINDINGS=Object.freeze({
 YDEX:'TECH_ISSUER_RISK_GATE_R1.8.32',
 X5:'RETAIL_ISSUER_RISK_GATE_R1.8.29',
 MOEX:'EXCHANGE_ISSUER_RISK_GATE_R1.8.30',
 SBER:'BANK_ISSUER_RISK_GATE_R1.8.28'
});
const REGISTRY={
 YDEX:{
  asOf:'2025-12-31',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'Yandex IR FY2025',sourceUrl:'https://ir.yandex.ru/financial-releases?report=q4&year=2025',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,riskLevel:'LOW',derivedBy:GATE_BINDINGS.YDEX,coverage:'TECH_GROWTH_MARGIN_LEVERAGE_LIQUIDITY_PROFITABILITY',items:['FY2025 revenue 1,441.1 bn RUB; growth about +31.7% y/y','Adjusted EBITDA 280.8 bn RUB; margin about 19.5%','Cash + equivalents + short-term deposits 250.2 bn RUB','Adjusted net debt / adjusted EBITDA 0.2x','Adjusted net profit 141.4 bn RUB; growth about +40.1% y/y','Model classification: LOW under R1.8.32 tech issuer-risk assumptions; sanctions/regulatory risk remains separate.']},
  sanctionsRegulatory:delegatedSanctions(['Separate primary-source sanctions/regulatory review required.'])
 },
 X5:{
  asOf:'2026-06-30',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'X5 H1 2026 IFRS financial results',sourceUrl:'https://www.x5.ru/ru/news/x5-obyavlyaet-o-roste-vyruchki-na-99-vo-2-kv-2026-g-rentabelnost-skorr-ebitda-do-primeneniya-msfo-ifrs-16-sostavila-60/',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,riskLevel:'MEDIUM',derivedBy:GATE_BINDINGS.X5,coverage:'RETAIL_GROWTH_MARGIN_LEVERAGE_PROFIT_RATING',items:['H1 2026 revenue 2,480,513 mn RUB, +10.5% y/y','H1 2026 adjusted EBITDA margin pre-IFRS 16: 5.7%','Net debt/EBITDA pre-IFRS 16 at 30 Jun 2026: 1.08x','H1 2026 net profit 34,482 mn RUB, -28.4% y/y','ACRA rating AAA(RU), stable, confirmed 24 Jun 2026','Expert RA rating ruAAA, stable, confirmed 29 Jul 2026','Model classification: MEDIUM because net profit declined y/y; thresholds are model assumptions, not rating-agency facts.'],ratingSources:['https://acra-ratings.ru/press-releases/7029/','https://raexpert.ru/releases/2026/jul29d']},
  sanctionsRegulatory:delegatedSanctions(['Separate primary-source sanctions/regulatory review required.'])
 },
 MOEX:{
  asOf:'2026-06-30',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'Moscow Exchange Q2 2026 IFRS results',sourceUrl:'https://www.moex.com/n103659',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,riskLevel:'LOW',derivedBy:GATE_BINDINGS.MOEX,coverage:'EXCHANGE_FEES_PROFIT_MARGIN_COSTS_LIQUIDITY_RATING',items:['Q2 2026 fee and commission income 22,271.7 mn RUB, +24.8% y/y','Q2 2026 net profit 15,766.2 mn RUB, +4.7% y/y','Q2 2026 adjusted EBITDA margin 67.6%','Q2 2026 total OPEX +10.4% y/y','Cash position at 30 Jun 2026: 194 bn RUB','Debt at 30 Jun 2026: 0','Expert RA reaffirmed ruAAA with stable outlook, disclosed in MOEX Q2 2026 results','Model classification: LOW financial issuer risk; thresholds are model assumptions. Sanctions/regulatory risk is assessed separately and remains material.']},
  sanctionsRegulatory:delegatedSanctions(['Use sanctions-regulatory-registry.js: financial issuer-risk verification cannot neutralize sanctions/designation risk.'])
 },
 SBER:{
  asOf:'2025-12-31',sourceStatus:'SOURCE_EXISTS',riskStatus:'VERIFIED',
  source:'MOEX issuer financials / Sber disclosure',sourceUrl:'https://www.moex.com/en/stocks/sber',
  issuer:{status:'VERIFIED',verified:true,critical:false,thesisBroken:false,riskLevel:'MEDIUM',derivedBy:GATE_BINDINGS.SBER,coverage:'BANK_ROE_CAPITAL_ASSET_QUALITY',items:['ROE 2025: 22.7%','CET1 2025: 12.3%','NPL 2025: 4.9%','Cost of Risk 2025: 1.30%','Model classification: MEDIUM because NPL >= 4% and Cost of Risk >= 1%; thresholds are model assumptions, not regulatory facts.']},
  sanctionsRegulatory:delegatedSanctions(['Use separate sanctions-regulatory registry; designation is material risk but not thesis destruction.'])
 }
};
function get(t){
 const k=String(t||'').toUpperCase();
 return REGISTRY[k]||{sourceStatus:'MISSING',riskStatus:'LOCK',issuer:lock(['Issuer absent from verified registry.']),sanctionsRegulatory:delegatedSanctions(['Sanctions/regulatory review absent.'])};
}
function audit(t){
 const k=String(t||'').toUpperCase(),r=get(k),i=r.issuer||{},s=r.sanctionsRegulatory||{};
 const sourceExists=r.sourceStatus==='SOURCE_EXISTS'&&!!r.source&&!!r.sourceUrl;
 const verifiedClaim=r.riskStatus==='VERIFIED'&&i.status==='VERIFIED'&&i.verified===true;
 const expectedGate=GATE_BINDINGS[k]||null;
 const sectorGateOk=!verifiedClaim||(!!expectedGate&&i.derivedBy===expectedGate);
 const riskVerified=verifiedClaim&&sourceExists&&sectorGateOk;
 const crossDomainOk=s.critical===undefined&&s.status==='DELEGATED';
 return {ticker:k,sourceExists,verifiedClaim,riskVerified,crossDomainOk,sectorGateOk,expectedGate,derivedBy:i.derivedBy||null,status:r.riskStatus||'LOCK',reason:!sourceExists?'source_missing':!crossDomainOk?'legacy_sanctions_semantics':!sectorGateOk?'sector_gate_binding_missing':riskVerified?'issuer_risk_verified':'issuer_risk_not_verified'};
}
function auditAll(){
 const errors=[],rows=[];
 for(const ticker of Object.keys(REGISTRY)){
  const a=audit(ticker); rows.push(a);
  if(!a.sourceExists) errors.push(ticker+':source_missing');
  if(!a.crossDomainOk) errors.push(ticker+':legacy_sanctions_semantics');
  if(!a.sectorGateOk) errors.push(ticker+':sector_gate_binding_missing');
  if(a.verifiedClaim&&!a.riskVerified) errors.push(ticker+':unreproducible_verified_claim');
 }
 return {ok:errors.length===0,coverage:rows.filter(x=>x.riskVerified).length+'/'+rows.length,rows,errors,rule:'VERIFIED issuer risk = primary source + exact sector-specific gate provenance + separate sanctions domain'};
}
global.InvestorRadarIssuerRisk={REGISTRY,GATE_BINDINGS,get,audit,auditAll};if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
