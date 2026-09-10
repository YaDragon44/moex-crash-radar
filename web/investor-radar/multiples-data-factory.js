// Investor Radar R1.8.9 — Multiples Data Factory
// Reproducible P/E only: verified EPS + dated MOEX close. No guessed peer values.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
const positive=x=>finite(x)&&Number(x)>0;
function yearOf(x){const d=String(x||'').slice(0,4),y=Number(d);return Number.isInteger(y)&&y>1900?y:null;}
function normalizeCandles(candles){return (Array.isArray(candles)?candles:[]).map(x=>({date:x?.date||x?.begin,close:Number(x?.close)})).filter(x=>/^\d{4}-\d{2}-\d{2}/.test(String(x.date))&&positive(x.close)).sort((a,b)=>String(a.date).localeCompare(String(b.date)));}
function yearEndPrices(candles){const out={};for(const x of normalizeCandles(candles)){const y=yearOf(x.date);if(y)out[y]=x;}return out;}
function normalizeEPS(series){return (Array.isArray(series)?series:[]).map(x=>Array.isArray(x)?{year:Number(x[0]),eps:Number(x[1]),verified:true}:{year:Number(x?.year),eps:Number(x?.eps),verified:x?.verified===true,source:x?.source||null,asOf:x?.asOf||null}).filter(x=>Number.isInteger(x.year)&&positive(x.eps));}
function historicalPE(input){
 const eps=normalizeEPS(input?.epsSeries),prices=yearEndPrices(input?.candles),points=[],missing=[];
 for(const e of eps){if(e.verified!==true){missing.push(`eps_${e.year}_unverified`);continue;}const p=prices[e.year];if(!p){missing.push(`price_${e.year}_missing`);continue;}points.push({year:e.year,date:p.date,price:p.close,eps:e.eps,pe:p.close/e.eps,priceSource:input?.priceSource||'MOEX ISS',epsSource:e.source||input?.epsSource||null,epsAsOf:e.asOf||null});}
 const verified=points.length>=3&&points.every(p=>positive(p.pe)&&!!p.priceSource&&!!p.epsSource);
 return {status:verified?'VERIFIED':'PARTIAL',verified,points,historicalPE:points.map(p=>p.pe),missing,method:'P/E = last available MOEX close in fiscal year / verified EPS for same fiscal year'};
}
function peerPE(input){
 const peers=(Array.isArray(input?.peers)?input.peers:[]),points=[],missing=[];
 for(const p of peers){if(!p?.ticker){missing.push('peer_ticker_missing');continue;}if(p.verified!==true||!positive(p.price)||!positive(p.eps)||!p.priceSource||!p.epsSource||!p.asOf){missing.push(`${p.ticker}_unverified`);continue;}points.push({ticker:p.ticker,price:Number(p.price),eps:Number(p.eps),pe:Number(p.price)/Number(p.eps),priceSource:p.priceSource,epsSource:p.epsSource,asOf:p.asOf});}
 const verified=points.length>=2;
 return {status:verified?'VERIFIED':'PARTIAL',verified,points,peerPE:points.map(p=>p.pe),missing,method:'Peer P/E = verified current/reference price / verified EPS; >=2 pre-approved peers required'};
}
function build(input){const h=historicalPE(input),p=peerPE(input);const verified=h.verified&&p.verified;return {status:verified?'VERIFIED':'PARTIAL',verified,historical:h,peers:p,historicalPE:h.historicalPE,peerPE:p.peerPE,missing:[...h.missing,...p.missing],source:verified?`${input?.priceSource||'MOEX ISS'} + verified issuer/peer EPS sources`:null,asOf:verified?(input?.asOf||new Date().toISOString().slice(0,10)):null};}
global.InvestorRadarMultiplesFactory={normalizeCandles,yearEndPrices,historicalPE,peerPE,build};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarMultiplesFactory;
})(typeof window!=='undefined'?window:globalThis);
