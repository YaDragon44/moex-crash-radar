// Investor Radar R1.8.3 — Full Risk Gate Foundation
// FACT metrics != model score != investment decision. Missing verified risk domains => PARTIAL/LOCK.
(function(global){
  'use strict';

  function finite(x){return Number.isFinite(Number(x));}
  function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
  function closes(candles){return (Array.isArray(candles)?candles:[]).map(x=>Number(x?.close)).filter(x=>Number.isFinite(x)&&x>0);}

  function maxDrawdown(candles){
    const a=closes(candles); if(a.length<2)return null;
    let peak=a[0],mdd=0;
    for(const p of a){if(p>peak)peak=p;const dd=(p/peak-1)*100;if(dd<mdd)mdd=dd;}
    return mdd;
  }

  function annualizedVolatility(candles){
    const a=closes(candles); if(a.length<3)return null;
    const r=[];for(let i=1;i<a.length;i++)r.push(Math.log(a[i]/a[i-1]));
    const mean=r.reduce((s,x)=>s+x,0)/r.length;
    const variance=r.reduce((s,x)=>s+(x-mean)**2,0)/(r.length-1);
    return Math.sqrt(variance)*Math.sqrt(252)*100;
  }

  // Model assumption: 60% annualized vol or -60% MDD maps the component to 100.
  function marketRiskScore(volatility,maxDD){
    if(!finite(volatility)||!finite(maxDD))return null;
    const volComponent=clamp(Number(volatility)/60*100,0,100);
    const ddComponent=clamp(Math.abs(Math.min(0,Number(maxDD)))/60*100,0,100);
    return 0.5*volComponent+0.5*ddComponent;
  }

  // Liquidity is a model layer, not a market fact. Inputs must come from MOEX marketdata.
  function liquidityRiskScore(turnoverRub,numTrades){
    if(!finite(turnoverRub)||!finite(numTrades)||Number(turnoverRub)<0||Number(numTrades)<0)return null;
    const v=Number(turnoverRub),n=Number(numTrades);
    // Transparent conservative buckets for screening only.
    const turnoverScore=v>=500e6?0:v>=100e6?20:v>=20e6?45:v>=5e6?70:100;
    const tradesScore=n>=5000?0:n>=1000?20:n>=300?45:n>=100?70:100;
    return 0.6*turnoverScore+0.4*tradesScore;
  }

  function classify(score){
    if(!finite(score))return 'UNKNOWN';
    if(score>=75)return 'HIGH';
    if(score>=45)return 'MEDIUM';
    return 'LOW';
  }

  function assess(candles,liquidity,issuer,regulatory){
    const valid=closes(candles).length;
    const vol=annualizedVolatility(candles),mdd=maxDrawdown(candles),marketScore=marketRiskScore(vol,mdd);
    const enoughHistory=valid>=120;
    const marketVerified=enoughHistory&&finite(vol)&&finite(mdd)&&finite(marketScore);

    const liqScore=liquidityRiskScore(liquidity?.turnoverRub,liquidity?.numTrades);
    const liquidityVerified=liquidity?.verified===true&&finite(liqScore);
    const issuerVerified=issuer?.verified===true;
    const regulatoryVerified=regulatory?.verified===true;
    const verified=marketVerified&&liquidityVerified&&issuerVerified&&regulatoryVerified;

    const score=marketVerified?(liquidityVerified?0.7*marketScore+0.3*liqScore:marketScore):null;
    const critical=Boolean(
      (marketVerified&&(vol>=80||mdd<=-60))||
      issuer?.critical===true||regulatory?.critical===true
    );

    const missing=[];
    if(!marketVerified)missing.push('market_history');
    if(!liquidityVerified)missing.push('liquidity');
    if(!issuerVerified)missing.push('issuer_fundamental_risk');
    if(!regulatoryVerified)missing.push('sanctions_regulatory_risk');

    return {
      scope:verified?'FULL':'PARTIAL',verified,
      marketVerified,liquidityVerified,issuerVerified,regulatoryVerified,
      status:verified?'VERIFIED':marketVerified?'PARTIAL':'LOCK',
      score:finite(score)?score:null,level:finite(score)?classify(score):'UNKNOWN',critical,
      metrics:{annualizedVolatility:vol,maxDrawdown:mdd,observations:valid,turnoverRub:finite(liquidity?.turnoverRub)?Number(liquidity.turnoverRub):null,numTrades:finite(liquidity?.numTrades)?Number(liquidity.numTrades):null,marketScore:finite(marketScore)?marketScore:null,liquidityScore:finite(liqScore)?liqScore:null},
      coverage:[marketVerified?'market':'market:LOCK',liquidityVerified?'liquidity':'liquidity:LOCK',issuerVerified?'issuer':'issuer:LOCK',regulatoryVerified?'regulatory':'regulatory:LOCK'],
      missing,
      items:[
        marketVerified?`Годовая волатильность: ${vol.toFixed(1)}%; максимальная просадка: ${mdd.toFixed(1)}%.`:'Недостаточно истории для подтверждённого market-risk расчёта.',
        liquidityVerified?`MOEX liquidity: turnover ${Number(liquidity.turnoverRub).toFixed(0)} ₽; trades ${Number(liquidity.numTrades).toFixed(0)}.`:'Liquidity gate не подтверждён.',
        issuerVerified?'Issuer fundamental risk подтверждён отдельным источником.':'Issuer fundamental risk не подтверждён.',
        regulatoryVerified?'Sanctions/regulatory risk подтверждён отдельным источником.':'Sanctions/regulatory risk не подтверждён.'
      ],
      model:'full score = 70% market score + 30% liquidity score; issuer/regulatory are mandatory verification gates and critical overrides',
      gateReason:verified?'Full risk gate PASS.':`Full risk gate LOCK: ${missing.join(', ')}.`
    };
  }

  global.InvestorRadarRisk={maxDrawdown,annualizedVolatility,marketRiskScore,liquidityRiskScore,classify,assess};
  if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarRisk;
})(typeof window!=='undefined'?window:globalThis);
