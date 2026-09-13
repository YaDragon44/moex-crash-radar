// Investor Radar R1.8.16 — Bank Quality Trend
// Descriptive trend control for banks. No valuation target and no recommendation by itself.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
function delta(a,b){return finite(a)&&finite(b)?Number(b)-Number(a):null;}
function assess(series){
 const years=Object.keys(series||{}).map(Number).filter(Number.isInteger).sort((a,b)=>a-b);
 if(years.length<2) return {status:'LOCK',verified:false,missing:['history_2y'],signals:[]};
 const first=series[years[0]],last=series[years[years.length-1]];
 const req=['roe','cet1','npl','costOfRisk'];
 const missing=[]; for(const k of req){ if(!finite(first?.[k])||!finite(last?.[k])) missing.push(k); }
 if(missing.length) return {status:'LOCK',verified:false,missing,signals:[]};
 const d={roe:delta(first.roe,last.roe),cet1:delta(first.cet1,last.cet1),npl:delta(first.npl,last.npl),costOfRisk:delta(first.costOfRisk,last.costOfRisk)};
 const signals=[];
 if(d.roe<0) signals.push('ROE_DOWN'); else if(d.roe>0) signals.push('ROE_UP');
 if(d.cet1>0) signals.push('CET1_UP'); else if(d.cet1<0) signals.push('CET1_DOWN');
 if(d.npl>0) signals.push('NPL_UP'); else if(d.npl<0) signals.push('NPL_DOWN');
 if(d.costOfRisk>0) signals.push('COR_UP'); else if(d.costOfRisk<0) signals.push('COR_DOWN');
 let traffic='GREEN';
 const bad=['ROE_DOWN','CET1_DOWN','NPL_UP','COR_UP'].filter(x=>signals.includes(x)).length;
 if(bad>=3) traffic='YELLOW';
 if(last.roe<15||last.cet1<10||last.npl>=6||last.costOfRisk>=2) traffic='RED';
 return {status:'VERIFIED',verified:true,traffic,from:years[0],to:years[years.length-1],delta:d,signals,method:'Trend only: ROE/CET1/NPL/Cost of Risk direction; does not set fair value or action'};
}
global.InvestorRadarBankQualityTrend={assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarBankQualityTrend;
})(typeof window!=='undefined'?window:globalThis);
