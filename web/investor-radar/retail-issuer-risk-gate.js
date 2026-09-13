// Investor Radar R1.8.29 — Retail Issuer Risk Gate
// Sector-specific issuer risk for food retail. Facts must be verified independently; thresholds are model assumptions.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
function assess(input={}){
 const required=['revenueGrowthPct','adjustedEbitdaMarginPct','netDebtToEbitda','netProfitGrowthPct'];
 const missing=[];
 for(const k of required) if(!finite(input[k])) missing.push(k);
 if(input.verified!==true) missing.push('verified_inputs');
 if(!input.source||!input.sourceUrl||!input.asOf) missing.push('source_metadata');
 if(input.ratingVerified!==true||!input.rating||!input.ratingSourceUrl) missing.push('credit_rating');
 if(missing.length) return {status:'LOCK',verified:false,riskLevel:'UNKNOWN',critical:false,thesisBroken:false,missing,items:[]};
 const rev=Number(input.revenueGrowthPct),margin=Number(input.adjustedEbitdaMarginPct),lev=Number(input.netDebtToEbitda),np=Number(input.netProfitGrowthPct);
 let riskLevel='LOW';
 if(lev>=3||margin<3||rev<0||np<=-50) riskLevel='HIGH';
 else if(lev>=2||margin<5||np<0||rev<5) riskLevel='MEDIUM';
 return {
  status:'VERIFIED',verified:true,riskLevel,critical:false,thesisBroken:false,
  coverage:'RETAIL_GROWTH_MARGIN_LEVERAGE_PROFIT_RATING',
  revenueGrowthPct:rev,adjustedEbitdaMarginPct:margin,netDebtToEbitda:lev,netProfitGrowthPct:np,
  rating:input.rating,ratingOutlook:input.ratingOutlook||null,
  source:input.source,sourceUrl:input.sourceUrl,ratingSourceUrl:input.ratingSourceUrl,asOf:input.asOf,
  items:[`Revenue growth ${rev}%`,`Adjusted EBITDA margin ${margin}%`,`Net debt/EBITDA ${lev}x`,`Net profit growth ${np}%`,`Credit rating ${input.rating}${input.ratingOutlook?' / '+input.ratingOutlook:''}`],
  method:'Retail issuer-risk model uses verified growth, margin, leverage, profit trend and credit rating. Thresholds are model assumptions; a negative profit trend does not automatically mean thesis destruction.'
 };
}
global.InvestorRadarRetailIssuerRisk={assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarRetailIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
