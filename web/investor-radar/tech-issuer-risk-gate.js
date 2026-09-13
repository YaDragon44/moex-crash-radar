// Investor Radar R1.8.32 — Tech Issuer Risk Gate
// Sector-specific financial issuer risk for a large technology/platform company.
// FACTS -> MODEL RISK. Sanctions/regulatory risk is a separate domain.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
function assess(input={}){
 const required=['revenueGrowthPct','adjustedEbitdaMarginPct','adjustedNetDebtToEbitda','cashAndShortTermDepositsBln','adjustedNetProfitGrowthPct'];
 const missing=[];
 for(const k of required) if(!finite(input[k])) missing.push(k);
 if(input.verified!==true) missing.push('verified_inputs');
 if(!input.source||!input.sourceUrl||!input.asOf) missing.push('source_metadata');
 if(missing.length) return {status:'LOCK',verified:false,riskLevel:'UNKNOWN',critical:false,thesisBroken:false,missing,items:[]};
 const revenueGrowth=Number(input.revenueGrowthPct);
 const margin=Number(input.adjustedEbitdaMarginPct);
 const leverage=Number(input.adjustedNetDebtToEbitda);
 const cash=Number(input.cashAndShortTermDepositsBln);
 const profitGrowth=Number(input.adjustedNetProfitGrowthPct);
 let riskLevel='LOW';
 // Model assumptions, not issuer guidance or rating-agency thresholds.
 if(revenueGrowth<=-15||margin<10||leverage>=3||cash<=0||profitGrowth<=-40) riskLevel='HIGH';
 else if(revenueGrowth<10||margin<15||leverage>=1.5||profitGrowth<0) riskLevel='MEDIUM';
 const critical=riskLevel==='HIGH'&&(leverage>=4||cash<=0||revenueGrowth<=-30||profitGrowth<=-60);
 return {
  status:'VERIFIED',verified:true,riskLevel,critical,thesisBroken:false,
  coverage:'TECH_GROWTH_MARGIN_LEVERAGE_LIQUIDITY_PROFITABILITY',
  revenueGrowthPct:revenueGrowth,adjustedEbitdaMarginPct:margin,adjustedNetDebtToEbitda:leverage,cashAndShortTermDepositsBln:cash,adjustedNetProfitGrowthPct:profitGrowth,
  source:input.source,sourceUrl:input.sourceUrl,asOf:input.asOf,
  items:[`Revenue growth ${revenueGrowth}%`,`Adjusted EBITDA margin ${margin}%`,`Adjusted net debt / adjusted EBITDA ${leverage}x`,`Cash + equivalents + short-term deposits ${cash} bn RUB`,`Adjusted net profit growth ${profitGrowth}%`],
  method:'Technology issuer-risk model uses verified growth, EBITDA margin, leverage, liquidity and adjusted profit trend. Thresholds are model assumptions. Sanctions/regulatory risk is assessed separately.'
 };
}
global.InvestorRadarTechIssuerRisk={assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarTechIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
