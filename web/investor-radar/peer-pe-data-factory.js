// Investor Radar R1.8.11 — Peer P/E Data Factory
// Price may be fetched from MOEX, but peer P/E is accepted only with verified positive EPS + source/asOf.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
const positive=x=>finite(x)&&Number(x)>0;
function build(universe,earnings,prices){
 const peers=Array.isArray(universe?.peers)?universe.peers:[],points=[],excluded=[];
 if(universe?.status!=='APPROVED_UNIVERSE')return {status:'LOCK',verified:false,points:[],peerPE:[],excluded:peers.map(t=>({ticker:t,reason:'universe_not_approved'})),missing:['approved_peer_universe']};
 for(const ticker of peers){
   const e=earnings?.get?earnings.get(ticker):earnings?.[ticker];
   const p=prices?.[ticker];
   if(e?.verified!==true||!positive(e?.eps)||!e?.source||!e?.asOf){excluded.push({ticker,reason:'verified_positive_eps_missing'});continue;}
   if(!positive(p?.price)||!p?.source||!p?.asOf){excluded.push({ticker,reason:'verified_price_missing'});continue;}
   points.push({ticker,price:Number(p.price),eps:Number(e.eps),pe:Number(p.price)/Number(e.eps),priceSource:p.source,epsSource:e.source,priceAsOf:p.asOf,epsAsOf:e.asOf});
 }
 const verified=points.length>=2;
 return {status:verified?'VERIFIED':'PARTIAL',verified,points,peerPE:points.map(x=>x.pe),excluded,missing:verified?[]:['peer_pe_2plus'],method:'Peer P/E = verified MOEX/reference price / verified positive EPS; only approved sector peers; >=2 valid peers required'};
}
global.InvestorRadarPeerPEFactory={build};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarPeerPEFactory;
})(typeof window!=='undefined'?window:globalThis);
