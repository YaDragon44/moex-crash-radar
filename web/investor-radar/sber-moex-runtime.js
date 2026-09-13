// Investor Radar R1.8.17 — SBER MOEX Runtime Collector
// Runtime-only market inputs. No hardcoded market prices.
(function(global){
'use strict';
const BASE='https://iss.moex.com/iss/engines/stock/markets/shares';
const positive=x=>Number.isFinite(Number(x))&&Number(x)>0;
function candleUrl(ticker,year){
 const t=String(ticker||'').toUpperCase();
 const y=Number(year);
 if(!/^[A-Z0-9]+$/.test(t)||!Number.isInteger(y)||y<2000||y>2100) throw new Error('invalid ticker/year');
 return `${BASE}/securities/${t}/candles.json?from=${y}-12-01&till=${y}-12-31&interval=24&iss.meta=off&iss.only=candles&candles.columns=begin,close`;
}
function quoteUrl(ticker){
 const t=String(ticker||'').toUpperCase();
 if(!/^[A-Z0-9]+$/.test(t)) throw new Error('invalid ticker');
 return `${BASE}/securities/${t}.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST,LCURRENTPRICE,UPDATETIME`;
}
function rows(block){
 const cols=Array.isArray(block?.columns)?block.columns:[];
 return (Array.isArray(block?.data)?block.data:[]).map(r=>Object.fromEntries(cols.map((c,i)=>[c,r[i]])));
}
function parseYearEnd(payload,year){
 const y=Number(year), rs=rows(payload?.candles).filter(x=>String(x.begin||'').startsWith(`${y}-`)&&positive(x.close));
 if(!rs.length) return {status:'LOCK',verified:false,year:y,reason:'no_valid_december_candles'};
 rs.sort((a,b)=>String(a.begin).localeCompare(String(b.begin)));
 const p=rs[rs.length-1];
 return {status:'VERIFIED',verified:true,year:y,date:String(p.begin).slice(0,10),close:Number(p.close),source:'MOEX ISS candles'};
}
function parseQuote(payload,ticker){
 const t=String(ticker||'').toUpperCase();
 const rs=rows(payload?.marketdata).filter(x=>String(x.SECID||'').toUpperCase()===t);
 const valid=rs.find(x=>positive(x.LAST))||rs.find(x=>positive(x.LCURRENTPRICE));
 if(!valid) return {status:'LOCK',verified:false,ticker:t,reason:'no_valid_market_price'};
 const price=positive(valid.LAST)?Number(valid.LAST):Number(valid.LCURRENTPRICE);
 return {status:'VERIFIED',verified:true,ticker:t,price,updateTime:valid.UPDATETIME||null,source:'MOEX ISS marketdata'};
}
async function getJson(url,fetchImpl){
 const f=fetchImpl||global.fetch;
 if(typeof f!=='function') throw new Error('fetch unavailable');
 const r=await f(url,{cache:'no-store'});
 if(!r||!r.ok) throw new Error(`MOEX HTTP ${r?.status||'ERR'}`);
 return r.json();
}
async function collect(fetchImpl){
 const years=[2023,2024,2025];
 const historical=[];
 for(const y of years){
  try{historical.push(parseYearEnd(await getJson(candleUrl('SBER',y),fetchImpl),y));}
  catch(e){historical.push({status:'LOCK',verified:false,year:y,reason:String(e.message||e)});}
 }
 const peers={};
 for(const t of ['VTBR','T']){
  try{peers[t]=parseQuote(await getJson(quoteUrl(t),fetchImpl),t);}
  catch(e){peers[t]={status:'LOCK',verified:false,ticker:t,reason:String(e.message||e)};}
 }
 const verified=historical.every(x=>x.verified)&&Object.values(peers).every(x=>x.verified);
 return {status:verified?'VERIFIED':'PARTIAL',verified,historical,peers,asOf:new Date().toISOString(),source:'MOEX ISS'};
}
global.InvestorRadarSberMoexRuntime={candleUrl,quoteUrl,parseYearEnd,parseQuote,collect};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberMoexRuntime;
})(typeof window!=='undefined'?window:globalThis);
