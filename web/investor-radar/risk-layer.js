// Investor Radar R1.8.26 — Integrated Risk Gate Semantics Hardening
// FACT metrics != model score != investment decision. Sanctions material/designated risk is explicit and never equals thesis destruction.
(function(global){
'use strict';
const finite=x=>Number.isFinite(Number(x));
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const closes=c=>(Array.isArray(c)?c:[]).map(x=>Number(x?.close)).filter(x=>Number.isFinite(x)&&x>0);
function maxDrawdown(c){const a=closes(c);if(a.length<2)return null;let peak=a[0],m=0;for(const p of a){if(p>peak)peak=p;const d=(p/peak-1)*100;if(d<m)m=d;}return m;}
function annualizedVolatility(c){const a=closes(c);if(a.length<3)return null;const r=[];for(let i=1;i<a.length;i++)r.push(Math.log(a[i]/a[i-1]));const mean=r.reduce((s,x)=>s+x,0)/r.length;const v=r.reduce((s,x)=>s+(x-mean)**2,0)/(r.length-1);return Math.sqrt(v)*Math.sqrt(252)*100;}
function marketRiskScore(vol,mdd){if(!finite(vol)||!finite(mdd))return null;return .5*clamp(+vol/60*100,0,100)+.5*clamp(Math.abs(Math.min(0,+mdd))/60*100,0,100);}
function liquidityRiskScore(turnoverRub,numTrades){if(!finite(turnoverRub)||!finite(numTrades)||+turnoverRub<0||+numTrades<0)return null;const v=+turnoverRub,n=+numTrades;const vs=v>=500e6?0:v>=100e6?20:v>=20e6?45:v>=5e6?70:100;const ns=n>=5000?0:n>=1000?20:n>=300?45:n>=100?70:100;return .6*vs+.4*ns;}
function classify(s){if(!finite(s))return'UNKNOWN';return s>=75?'HIGH':s>=45?'MEDIUM':'LOW';}
function assess(candles,liquidity,issuer,regulatory){
 const valid=closes(candles).length,vol=annualizedVolatility(candles),mdd=maxDrawdown(candles),marketScore=marketRiskScore(vol,mdd);
 const marketVerified=valid>=120&&finite(vol)&&finite(mdd)&&finite(marketScore);
 const liqScore=liquidityRiskScore(liquidity?.turnoverRub,liquidity?.numTrades),liquidityVerified=liquidity?.verified===true&&finite(liqScore);
 const issuerVerified=issuer?.verified===true,regulatoryVerified=regulatory?.verified===true;
 const verified=marketVerified&&liquidityVerified&&issuerVerified&&regulatoryVerified;
 const score=marketVerified?(liquidityVerified?0.7*marketScore+0.3*liqScore:marketScore):null;
 const marketCritical=marketVerified&&(vol>=80||mdd<=-60);
 const issuerCritical=issuer?.critical===true;
 const sanctionsLevel=regulatoryVerified?(regulatory?.level||'UNKNOWN'):'UNKNOWN';
 const sanctionsMaterial=regulatoryVerified&&regulatory?.material===true;
 const sanctionsDesignated=regulatoryVerified&&regulatory?.designated===true;
 const thesisBroken=issuer?.thesisBroken===true;
 const missing=[];if(!marketVerified)missing.push('market_history');if(!liquidityVerified)missing.push('liquidity');if(!issuerVerified)missing.push('issuer_fundamental_risk');if(!regulatoryVerified)missing.push('sanctions_regulatory_risk');
 return {scope:verified?'FULL':'PARTIAL',verified,marketVerified,liquidityVerified,issuerVerified,regulatoryVerified,status:verified?'VERIFIED':marketVerified?'PARTIAL':'LOCK',score:finite(score)?score:null,level:finite(score)?classify(score):'UNKNOWN',critical:marketCritical||issuerCritical,thesisBroken,sanctions:{verified:regulatoryVerified,level:sanctionsLevel,material:sanctionsMaterial,designated:sanctionsDesignated,status:regulatory?.status||'LOCK',items:regulatory?.items||[]},metrics:{annualizedVolatility:vol,maxDrawdown:mdd,observations:valid,turnoverRub:finite(liquidity?.turnoverRub)?+liquidity.turnoverRub:null,numTrades:finite(liquidity?.numTrades)?+liquidity.numTrades:null,marketScore:finite(marketScore)?marketScore:null,liquidityScore:finite(liqScore)?liqScore:null},coverage:[marketVerified?'market':'market:LOCK',liquidityVerified?'liquidity':'liquidity:LOCK',issuerVerified?'issuer':'issuer:LOCK',regulatoryVerified?'regulatory':'regulatory:LOCK'],missing,items:[marketVerified?`Годовая волатильность: ${vol.toFixed(1)}%; максимальная просадка: ${mdd.toFixed(1)}%.`:'Недостаточно истории для подтверждённого market-risk расчёта.',liquidityVerified?`MOEX liquidity: turnover ${(+liquidity.turnoverRub).toFixed(0)} ₽; trades ${(+liquidity.numTrades).toFixed(0)}.`:'Liquidity gate не подтверждён.',...(issuer?.items||[issuerVerified?'Issuer risk подтверждён.':'Issuer risk не подтверждён.']),...(regulatory?.items||[regulatoryVerified?'Sanctions/regulatory risk подтверждён.':'Sanctions/regulatory risk не подтверждён.'])],model:'score = 70% market + 30% liquidity; issuer/regulatory are mandatory gates; sanctions material/designated do not imply thesisBroken or issuer critical risk',gateReason:verified?'Full risk gate PASS.':`Full risk gate LOCK: ${missing.join(', ')}.`};
}
global.InvestorRadarRisk={maxDrawdown,annualizedVolatility,marketRiskScore,liquidityRiskScore,classify,assess};if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarRisk;
})(typeof window!=='undefined'?window:globalThis);
