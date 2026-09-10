// Investor Radar R1.8.19 — SBER Book Value / P-B Gate
// Prevents silent use of total regulatory capital as common book value.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
const positive=x=>finite(x)&&Number(x)>0;

function assess(input){
  const missing=[];
  const equity=Number(input?.commonEquityAttributableRub);
  const shares=Number(input?.commonSharesOutstanding);
  const price=Number(input?.price);
  if(input?.verified!==true) missing.push('verified_inputs');
  if(!positive(equity)) missing.push('common_equity_attributable');
  if(!positive(shares)) missing.push('common_shares_outstanding');
  if(!positive(price)) missing.push('market_price');
  if(input?.preferredTreatmentVerified!==true) missing.push('preferred_share_treatment');
  if(!input?.equitySource||!input?.shareSource||!input?.priceSource||!input?.asOf) missing.push('source_metadata');
  if(missing.length){
    return {status:'LOCK',verified:false,missing,bvps:null,pb:null,method:'LOCK until common attributable equity + common share basis + preferred-share treatment + market price are verified'};
  }
  const bvps=equity/shares;
  const pb=price/bvps;
  if(!positive(bvps)||!positive(pb)) return {status:'LOCK',verified:false,missing:['positive_bvps_pb'],bvps:null,pb:null};
  return {
    status:'VERIFIED',verified:true,missing:[],bvps,pb,
    commonEquityAttributableRub:equity,commonSharesOutstanding:shares,price,
    equitySource:input.equitySource,shareSource:input.shareSource,priceSource:input.priceSource,asOf:input.asOf,
    method:'BVPS = verified common equity attributable / verified common shares outstanding; P/B = verified market price / BVPS'
  };
}

function fromTotalCapital(){
  return {status:'LOCK',verified:false,missing:['common_equity_attributable','common_shares_outstanding','preferred_share_treatment'],bvps:null,pb:null,reason:'Total equity/capital must not be treated as common BVPS without attribution and share-basis verification'};
}

global.InvestorRadarSberBookValueGate={assess,fromTotalCapital};
if(typeof module!=='undefined'&&module.exports) module.exports=global.InvestorRadarSberBookValueGate;
})(typeof window!=='undefined'?window:globalThis);
