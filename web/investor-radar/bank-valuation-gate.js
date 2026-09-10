// Investor Radar R1.8.15 — Bank Valuation Gate
// Bank-specific control. No fair-value output unless P/B, ROE and asset-quality inputs are verified.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
function assess(input){
 const missing=[];
 const req=['price','bookValuePerShare','roe','cet1','npl','costOfRisk'];
 for(const k of req) if(!finite(input?.[k])) missing.push(k);
 if(input?.verified!==true) missing.push('verified_inputs');
 if(!input?.source||!input?.asOf) missing.push('source_metadata');
 if(missing.length) return {status:'LOCK',verified:false,missing,pb:null,quality:null};
 const price=Number(input.price),bvps=Number(input.bookValuePerShare),roe=Number(input.roe),cet1=Number(input.cet1),npl=Number(input.npl),cor=Number(input.costOfRisk);
 if(price<=0||bvps<=0) return {status:'LOCK',verified:false,missing:['positive_price_bvps'],pb:null,quality:null};
 const pb=price/bvps;
 // Quality flag is descriptive, not a valuation target.
 let quality='GREEN';
 if(roe<15||cet1<10||npl>=6||cor>=2) quality='RED';
 else if(roe<20||npl>=4||cor>=1) quality='YELLOW';
 return {status:'VERIFIED',verified:true,missing:[],pb,roe,cet1,npl,costOfRisk:cor,quality,source:input.source,asOf:input.asOf,method:'P/B = market price / verified book value per share; ROE/CET1/NPL/Cost of Risk are independent bank-quality controls'};
}
function combine(peGate,bankGate){
 const verified=peGate?.verified===true&&bankGate?.verified===true;
 return {status:verified?'VERIFIED':'PARTIAL',verified,peStatus:peGate?.status||'LOCK',bankStatus:bankGate?.status||'LOCK',reason:verified?'Both P/E and bank-specific P/B+quality gates verified':'Valuation remains blocked until both independent gates are verified'};
}
global.InvestorRadarBankValuation={assess,combine};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarBankValuation;
})(typeof window!=='undefined'?window:globalThis);
