// Investor Radar R1.8.45 — SBER P/B Runtime Integration
// Direct issuer-reported common BVPS + live MOEX TQBR SBER price. Fail closed.
(function(global){
'use strict';
const TQBR_URL='https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SBER.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST,LCURRENTPRICE,UPDATETIME';
function deps(){
 const bvps=global.InvestorRadarSberReportedBVPS||(typeof require==='function'?require('./sber-reported-bvps-registry.js'):null);
 const moex=global.InvestorRadarSberMoexRuntime||(typeof require==='function'?require('./sber-moex-runtime.js'):null);
 const bank=global.InvestorRadarBankValuation||(typeof require==='function'?require('./bank-valuation-gate.js'):null);
 const reg=global.InvestorRadarSberValuation||(typeof require==='function'?require('./sber-valuation-registry.js'):null);
 return {bvps,moex,bank,reg};
}
function assessFromQuotePayload(payload,marketAsOf){
 const {bvps,moex,bank,reg}=deps();
 if(!bvps||!moex||!bank||!reg) return {status:'LOCK',verified:false,missing:['dependencies'],pb:null};
 const b=bvps.assess();
 const q=moex.parseQuote(payload,'SBER');
 const m=reg.SBER?.bankMetrics?.[2025];
 const missing=[];
 if(b?.verified!==true) missing.push('issuer_reported_bvps');
 if(q?.verified!==true) missing.push('moex_sber_price');
 if(!m) missing.push('bank_metrics_2025');
 if(missing.length) return {status:'LOCK',verified:false,missing,pb:null,bvpsStatus:b?.status||'LOCK',priceStatus:q?.status||'LOCK'};
 const asOf=marketAsOf||q.updateTime||new Date().toISOString();
 const result=bank.assess({price:q.price,bookValuePerShare:b.bookValuePerShare,roe:m.roe,cet1:m.cet1,npl:m.npl,costOfRisk:m.costOfRisk,verified:true,source:'MOEX ISS TQBR market price + Sberbank Annual Report 2025 issuer-reported net assets per common share + verified SBER 2025 bank metrics',asOf});
 return {...result,ticker:'SBER',price:q.price,bookValuePerShare:b.bookValuePerShare,bvpsAsOf:b.asOf,marketAsOf:asOf,bvpsSource:b.source,bvpsLocator:b.locator,priceSource:q.source,formula:'P/B = MOEX SBER market price / 390.02 RUB issuer-reported net assets per common share'};
}
async function collect(fetchImpl){
 const f=fetchImpl||global.fetch;
 if(typeof f!=='function') return {status:'LOCK',verified:false,missing:['fetch_unavailable'],pb:null};
 try{
  const r=await f(TQBR_URL,{cache:'no-store'});
  if(!r||!r.ok) return {status:'LOCK',verified:false,missing:[`moex_http_${r?.status||'ERR'}`],pb:null};
  return assessFromQuotePayload(await r.json(),new Date().toISOString());
 }catch(e){return {status:'LOCK',verified:false,missing:[String(e.message||e)],pb:null};}
}
global.InvestorRadarSberPBRuntime={TQBR_URL,assessFromQuotePayload,collect};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberPBRuntime;
})(typeof window!=='undefined'?window:globalThis);
