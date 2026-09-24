// Investor Radar R1.9.0 — independent trader decision layer.
// Uses only MOEX OHLCV supplied by runtime. Portfolio context is deliberately absent.
// Missing data => fail closed. Wyckoff/Elliott are not inferred by this layer.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
const nums=(a,k)=>a.map(x=>Number(x[k])).filter(finite);
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
const median=a=>{a=a.filter(finite).map(Number).sort((x,y)=>x-y);if(!a.length)return null;let m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2};
const sma=(a,n,k='close')=>a.length>=n?mean(a.slice(-n).map(x=>Number(x[k]))):null;
function atr(a,n=14){if(a.length<n+1)return null;const tr=[];for(let i=a.length-n;i<a.length;i++){const x=a[i],p=a[i-1];tr.push(Math.max(+x.high-+x.low,Math.abs(+x.high-+p.close),Math.abs(+x.low-+p.close)))}return mean(tr)}
function rsi(a,n=14){if(a.length<n+1)return null;let g=0,l=0;for(let i=a.length-n;i<a.length;i++){let d=+a[i].close-+a[i-1].close;if(d>0)g+=d;else l-=d}if(l===0)return 100;let rs=(g/n)/(l/n);return 100-100/(1+rs)}
function vwap(a){let pv=0,v=0;for(const x of a){let q=+x.volume;if(!finite(q)||q<=0)continue;pv+=((+x.high+ +x.low+ +x.close)/3)*q;v+=q}return v?pv/v:null}
function aggregate4h(h){const out=[];let cur=null;for(const x of h){let d=new Date(x.begin),day=x.begin.slice(0,10),hour=d.getHours(),bucket=Math.floor(hour/4);let key=day+'-'+bucket;if(!cur||cur.key!==key){cur={key,begin:x.begin,open:+x.open,high:+x.high,low:+x.low,close:+x.close,volume:+x.volume||0};out.push(cur)}else{cur.high=Math.max(cur.high,+x.high);cur.low=Math.min(cur.low,+x.low);cur.close=+x.close;cur.volume+=(+x.volume||0)}}return out}
function ret(a,n=20){if(a.length<n+1)return null;let x=+a.at(-1).close,y=+a.at(-1-n).close;return y>0?(x/y-1)*100:null}
function grade(s){return s>=16?'A+':s>=13?'A':s>=10?'B':s>=7?'C':'D'}
function assess(input){
 const d=input?.daily||[],h=input?.hourly||[],m=input?.marketDaily||[],price=+input?.price;
 const missing=[];if(!finite(price))missing.push('current_price');if(d.length<60)missing.push('D1_60');if(h.length<40)missing.push('H1_40');if(m.length<25)missing.push('IMOEX_D1_25');
 if(missing.length)return {verified:false,status:'WAIT',direction:'NO_TRADE',missing,reason:'insufficient_market_data',score:0,grade:'D'};
 const h4=aggregate4h(h);if(h4.length<20)return {verified:false,status:'WAIT',direction:'NO_TRADE',missing:['H4_20'],reason:'insufficient_H4_data',score:0,grade:'D'};
 const dc=+d.at(-1).close,d20=sma(d,20),d50=sma(d,50),h4c=+h4.at(-1).close,h420=sma(h4,20);
 const longBias=dc>d20&&d20>d50&&h4c>h420,shortBias=dc<d20&&d20<d50&&h4c<h420;
 if(!longBias&&!shortBias)return {verified:true,status:'NO_TRADE',direction:'NO_TRADE',reason:'D1_H4_bias_not_aligned',score:0,grade:'D',asOf:h.at(-1).begin};
 const direction=longBias?'LONG':'SHORT',prior=h.slice(-11,-1),last=h.at(-1),breakLevel=longBias?Math.max(...prior.map(x=>+x.high)):Math.min(...prior.map(x=>+x.low));
 const trigger=longBias?+last.close>breakLevel:+last.close<breakLevel;
 const ha=atr(h,14),da=atr(d,14);if(!finite(ha)||!finite(da)||ha<=0||da<=0)return {verified:false,status:'WAIT',direction,missing:['ATR'],reason:'atr_unavailable',score:0,grade:'D'};
 const swing=h.slice(-10),support=Math.min(...swing.map(x=>+x.low)),resistance=Math.max(...swing.map(x=>+x.high));
 const entryLow=longBias?breakLevel:breakLevel-0.25*ha,entryHigh=longBias?breakLevel+0.25*ha:breakLevel;
 const entry=trigger?+last.close:breakLevel,stop=longBias?support-0.15*ha:resistance+0.15*ha,risk=Math.abs(entry-stop);
 if(!finite(risk)||risk<=0)return {verified:false,status:'WAIT',direction,missing:['valid_stop'],reason:'risk_geometry_invalid',score:0,grade:'D'};
 const tp1=longBias?entry+da:entry-da,tp2=longBias?entry+2*da:entry-2*da,tp3=longBias?entry+3*da:entry-3*da,rr=Math.abs(tp2-entry)/risk;
 const volMed=median(h.slice(-20).map(x=>+x.volume)),volRatio=volMed>0?(+last.volume/volMed):null;
 const rv=rsi(h,14),today=h.filter(x=>x.begin.slice(0,10)===last.begin.slice(0,10)),vw=vwap(today.length?today:h.slice(-10));
 const dh=d.slice(-20),hi=Math.max(...dh.map(x=>+x.high)),lo=Math.min(...dh.map(x=>+x.low)),range=hi-lo,fibs=range>0?[hi-.382*range,hi-.5*range,hi-.618*range]:[],fibNear=fibs.some(x=>Math.abs(entry-x)<=.25*da);
 const tickerRet=ret(d,20),marketRet=ret(m,20),rsOk=finite(tickerRet)&&finite(marketRet)&&(longBias?tickerRet>marketRet:tickerRet<marketRet);
 const md20=sma(m,20),mc=+m.at(-1).close,marketAligned=longBias?mc>md20:mc<md20;
 const structure=longBias?(+last.close>+h.at(-6).close):(+last.close<+h.at(-6).close);
 const levelNear=Math.abs(entry-breakLevel)<=.25*ha;
 const momentum=finite(rv)&&(longBias?(rv>=50&&rv<=72):(rv>=28&&rv<=50));
 const vwapOk=finite(vw)&&(longBias?+last.close>=vw:+last.close<=vw);
 const components={trend:2,structure:structure?2:1,level:levelNear?2:1,volume:finite(volRatio)?(volRatio>=1.2?2:volRatio>=.8?1:0):0,wyckoff:0,elliott:0,fibonacci:fibNear?1:0,vwap:vwapOk?1:0,momentum:momentum?1:0,relativeStrength:rsOk?1:0,rr:rr>=3?3:rr>=2?2:rr>=1.5?1:0,market:marketAligned?2:0};
 const score=Object.values(components).reduce((s,x)=>s+x,0),g=grade(score);
 const status=trigger&&score>=13&&rr>=2?'READY':'WAIT';
 return {verified:true,status,direction,reason:status==='READY'?'trigger_confirmed':'setup_without_A_trigger',asOf:last.begin,observation:{low:Math.min(entryLow,entryHigh),high:Math.max(entryLow,entryHigh)},entry:{low:Math.min(entryLow,entryHigh),high:Math.max(entryLow,entryHigh)},trigger:{level:breakLevel,text:(longBias?'H1 close > ':'H1 close < ')+breakLevel.toFixed(2)},stop,invalidation:stop,tp1,tp2,tp3,rr,score,grade:g,components,metrics:{atrD1:da,atrH1:ha,rsiH1:rv,vwapSession:vw,volumeRatio:volRatio,tickerReturn20:tickerRet,marketReturn20:marketRet},source:'MOEX ISS OHLCV · D1 + H1; H4 derived from H1',portfolioIndependent:true};
}
global.InvestorRadarTrader={assess,aggregate4h,atr,rsi,grade};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarTrader;
})(typeof window!=='undefined'?window:globalThis);
