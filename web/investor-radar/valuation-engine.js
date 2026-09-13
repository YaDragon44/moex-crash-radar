// Investor Radar R1.8.7 — Valuation Gate Hardening
// No hardcoded hurdle-rate valuation. VERIFIED requires explicit, source-backed multiple history and peer set.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
const validPositive=x=>finite(x)&&Number(x)>0;
function median(xs){const a=(Array.isArray(xs)?xs:[]).map(Number).filter(validPositive).sort((a,b)=>a-b);if(!a.length)return null;const m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;}
function assess(input){
 const eps=Number(input?.eps),hist=Array.isArray(input?.historicalPE)?input.historicalPE:[],peers=Array.isArray(input?.peerPE)?input.peerPE:[];
 const hMed=median(hist),pMed=median(peers);
 const missing=[];
 if(input?.epsVerified!==true||!validPositive(eps))missing.push('verified_eps');
 if(hist.filter(validPositive).length<3)missing.push('historical_pe_3plus');
 if(peers.filter(validPositive).length<2)missing.push('peer_pe_2plus');
 if(!input?.source||!input?.asOf)missing.push('source_metadata');
 const verified=missing.length===0;
 if(!verified)return {status:'LOCK',verified:false,low:null,high:null,anchorPE:null,historicalMedianPE:hMed,peerMedianPE:pMed,missing,method:'LOCK until verified EPS + >=3 historical P/E + >=2 peer P/E + source/asOf'};
 // Transparent model assumption: 60% own historical median + 40% peer median; ±15% fair-value band.
 const anchorPE=0.6*hMed+0.4*pMed,mid=eps*anchorPE;
 return {status:'VERIFIED',verified:true,low:mid*0.85,high:mid*1.15,mid,anchorPE,historicalMedianPE:hMed,peerMedianPE:pMed,missing:[],source:input.source,asOf:input.asOf,method:'fair value = EPS × (0.6×historical median P/E + 0.4×peer median P/E); band ±15%'};
}
global.InvestorRadarValuation={median,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarValuation;
})(typeof window!=='undefined'?window:globalThis);
