// Investor Radar R1.8.4 — Issuer Risk Registry Foundation
// Only primary-source verified facts are allowed. Missing domains stay LOCK.
(function(global){'use strict';
const REGISTRY={
 YDEX:{asOf:'2025-12-31',source:'Yandex IR FY2025',sourceUrl:'https://ir.yandex.ru/financial-releases?report=q4&year=2025',issuer:{verified:true,critical:false,items:['FY2025 revenue 1,441.1 bn RUB','Adjusted EBITDA 280.8 bn RUB','Cash + equivalents + short-term deposits 250.2 bn RUB','Adjusted net debt / adjusted EBITDA 0.2x']},sanctionsRegulatory:{verified:false,critical:false,items:['Not verified in R1.8.4; separate primary-source review required.']}},
 X5:{asOf:'2026-06-30',source:'X5 official financial statements/results',sourceUrl:'https://www.x5.ru/ru/investors/financial-statements/',issuer:{verified:true,critical:false,items:['Official FY2025 audited IFRS statements published 20 Mar 2026','Official H1 2026 IFRS statements published 13 Aug 2026']},sanctionsRegulatory:{verified:false,critical:false,items:['Not verified in R1.8.4; separate primary-source review required.']}},
 MOEX:{asOf:'2026-06-30',source:'Moscow Exchange official IFRS/Annual Report',sourceUrl:'https://www.moex.com/s1355',issuer:{verified:true,critical:false,items:['FY2025 IFRS statements published 5 Mar 2026','H1 2026 interim IFRS statements published 26 Aug 2026']},sanctionsRegulatory:{verified:false,critical:false,items:['Not verified in R1.8.4; separate primary-source review required.']}},
 SBER:{asOf:null,source:null,sourceUrl:null,issuer:{verified:false,critical:false,items:['Недостаточно проверенных данных в текущем R1.8.4 registry.']},sanctionsRegulatory:{verified:false,critical:false,items:['Not verified in R1.8.4; separate primary-source review required.']}}
};
function get(t){return REGISTRY[t]||{issuer:{verified:false,critical:false,items:['Issuer absent from verified registry.']},sanctionsRegulatory:{verified:false,critical:false,items:['Sanctions/regulatory review absent.']}}}
global.InvestorRadarIssuerRisk={REGISTRY,get};if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
