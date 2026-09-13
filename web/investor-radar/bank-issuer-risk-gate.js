// Investor Radar R1.8.28 — Bank Issuer Risk Gate
// Bank-specific issuer-risk verification from primary-source profitability, capital and asset-quality metrics.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
function assess(input={}){
 const missing=[];
 for(const k of ['roe','cet1','npl','costOfRisk']) if(!finite(input[k])) missing.push(k);
 if(input.verified!==true) missing.push('verified_inputs');
 if(!input.source||!input.sourceUrl||!input.asOf) missing.push('source_metadata');
 if(missing.length) return {status:'LOCK',verified:false,riskLevel:'UNKNOWN',critical:false,thesisBroken:false,missing,items:[]};
 const roe=Number(input.roe),cet1=Number(input.cet1),npl=Number(input.npl),cor=Number(input.costOfRisk);
 let riskLevel='LOW';
 // Model thresholds, not regulatory facts. Used only to classify verified issuer-risk evidence.
 if(cet1<10||npl>=6||cor>=2||roe<15) riskLevel='HIGH';
 else if(npl>=4||cor>=1||roe<20) riskLevel='MEDIUM';
 return {
  status:'VERIFIED',verified:true,riskLevel,critical:false,thesisBroken:false,
  coverage:'BANK_ROE_CAPITAL_ASSET_QUALITY',roe,cet1,npl,costOfRisk:cor,
  source:input.source,sourceUrl:input.sourceUrl,asOf:input.asOf,
  items:[`ROE ${roe}%`,`CET1 ${cet1}%`,`NPL ${npl}%`,`Cost of Risk ${cor}%`],
  method:'Issuer risk uses verified bank-specific ROE/CET1/NPL/Cost of Risk. Thresholds are model assumptions and do not by themselves imply thesis destruction.'
 };
}
global.InvestorRadarBankIssuerRisk={assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarBankIssuerRisk;
})(typeof window!=='undefined'?window:globalThis);
