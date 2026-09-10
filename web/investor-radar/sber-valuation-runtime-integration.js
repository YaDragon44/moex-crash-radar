// Investor Radar R1.8.18 — SBER Valuation Runtime Integration
// Combines verified SBER EPS, runtime MOEX year-end prices, and approved peer EPS/prices.
(function(global){
'use strict';
function build(input){
 const R=input?.registry, M=input?.runtime, F=input?.multiplesFactory, U=input?.peerUniverse, E=input?.peerEarnings, P=input?.peerPEFactory;
 const missing=[];
 if(!R?.SBER||!Array.isArray(R.SBER.epsSeries)) missing.push('sber_registry');
 if(M?.verified!==true) missing.push('moex_runtime_verified');
 if(!F?.historicalPE) missing.push('multiples_factory');
 if(!U?.validate) missing.push('peer_universe');
 if(!E?.get) missing.push('peer_earnings');
 if(!P?.build) missing.push('peer_pe_factory');
 if(missing.length) return {status:'LOCK',verified:false,missing,historical:null,peers:null};
 const candles=(M.historical||[]).filter(x=>x?.verified===true).map(x=>({date:x.date,close:x.close}));
 const historical=F.historicalPE({epsSeries:R.SBER.epsSeries,candles,priceSource:'MOEX ISS candles'});
 const universe=U.validate('SBER');
 const prices={};
 for(const t of universe.peers||[]){
   const q=M.peers?.[t];
   if(q?.verified===true) prices[t]={price:q.price,source:q.source||'MOEX ISS marketdata',asOf:q.updateTime||M.asOf};
 }
 const peers=P.build(universe,E,prices);
 const verified=historical.verified===true&&peers.verified===true;
 return {status:verified?'VERIFIED':'PARTIAL',verified,historical,peers,source:verified?'MOEX ISS + verified issuer EPS registries':null,asOf:verified?M.asOf:null,missing:[...(historical.missing||[]),...(peers.missing||[])]};
}
global.InvestorRadarSberValuationRuntimeIntegration={build};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberValuationRuntimeIntegration;
})(typeof window!=='undefined'?window:globalThis);
