// Investor Radar R1.8.30 — Exchange Issuer Risk Gate
// Sector-specific financial issuer risk for an exchange/infrastructure operator.
// Sanctions/regulatory risk is intentionally assessed in a separate domain.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
function assess(input={}){
 const required=['feeIncomeGrowthPct','netProfitGrowthPct','adjustedEbitdaMarginPct','opexGrowthPct','cashPositionBln','debtBln'];
 const missing=[];
 for(const k of required) if(!finite(input[k])) missing.push(k);
 if(input.verified!==true) missing.push('verified_inputs');
 if(!input.source||!input.sourceUrl||!input.asOf) missing.push('source_metadata');
 if(input.ratingVerified!==true||!input.rating||!input.ratingSource) missing.push('credit_rating');
 if(missing.length) return {status:'LOCK',verified:false,riskLevel:'UNKNOWN',critical:false,thesisBroken:false,missing,items:[]};
 const fee=Number(input.feeIncomeGrowthPct),profit=Number(input.netProfitGrowthPct),margin=Number(input.adjustedEbitdaMarginPct),opex=Number(input.opexGrowthPct),cash=Number(input.cashPositionBln),debt=Number(input.debtBln);
 let riskLevel='LOW';
 // Model assumptions, not rating-agency or regulatory thresholds.
 if(fee<=-20||profit<=-40||margin<45||debt>cash) riskLevel='HIGH';
 else if(fee<0||profit<0||margin<60||opex>=20||debt>0) riskLevel='MEDIUM';
 return {
  status:'VERIFIED',verified:true,riskLevel,critical:false,thesisBroken:false,
  coverage:'EXCHANGE_FEES_PROFIT_MARGIN_COSTS_LIQUIDITY_RATING',
  feeIncomeGrowthPct:fee,netProfitGrowthPct:profit,adjustedEbitdaMarginPct:margin,opexGrowthPct:opex,cashPositionBln:cash,debtBln:debt,
  rating:input.rating,ratingOutlook:input.ratingOutlook||null,
  source:input.source,sourceUrl:input.sourceUrl,ratingSource:input.ratingSource,asOf:input.asOf,
  items:[`Fee income growth ${fee}%`,`Net profit growth ${profit}%`,`Adjusted EBITDA margin ${margin}%`,`Total OPEX growth ${opex}%`,`Cash position ${cash} bn RUB`,`Debt ${debt} bn RUB`,`Credit rating ${input.rating}${input.ratingOutlook?' / '+input.ratingOutlook:''}`],
  method:'Exchange issuer-risk model uses verified fee growth, profit trend, EBITDA margin, cost growth, cash/debt position and credit rating. Thresholds are model assumptions. Sanctions/regulatory risk is a separate gate and cannot be neutralized by a LOW financial-risk score.'
 };
}
global.InvestorRadarExchangeIssuerRisk={assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarExchangeIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
