// Investor Radar R1.8.2 — Market Risk Layer Foundation
// Model risk metrics from MOEX price history. FACT metrics != full issuer risk assessment.
(function(global){
  'use strict';

  function finite(x){return Number.isFinite(Number(x));}
  function clamp(x,a,b){return Math.max(a,Math.min(b,x));}
  function closes(candles){return (Array.isArray(candles)?candles:[]).map(x=>Number(x?.close)).filter(x=>Number.isFinite(x)&&x>0);}

  function maxDrawdown(candles){
    const a=closes(candles); if(a.length<2)return null;
    let peak=a[0],mdd=0;
    for(const p of a){ if(p>peak)peak=p; const dd=(p/peak-1)*100; if(dd<mdd)mdd=dd; }
    return mdd;
  }

  function annualizedVolatility(candles){
    const a=closes(candles); if(a.length<3)return null;
    const r=[]; for(let i=1;i<a.length;i++)r.push(Math.log(a[i]/a[i-1]));
    const mean=r.reduce((s,x)=>s+x,0)/r.length;
    const variance=r.reduce((s,x)=>s+(x-mean)**2,0)/(r.length-1);
    return Math.sqrt(variance)*Math.sqrt(252)*100;
  }

  // Transparent model assumptions, not market facts:
  // 50% volatility + 50% drawdown. 60% annualized vol or -60% MDD maps each component to 100.
  function marketRiskScore(volatility,maxDD){
    if(!finite(volatility)||!finite(maxDD))return null;
    const volComponent=clamp(Number(volatility)/60*100,0,100);
    const ddComponent=clamp(Math.abs(Math.min(0,Number(maxDD)))/60*100,0,100);
    return 0.5*volComponent+0.5*ddComponent;
  }

  function classify(score){
    if(!finite(score))return 'UNKNOWN';
    if(score>=75)return 'HIGH';
    if(score>=45)return 'MEDIUM';
    return 'LOW';
  }

  function assess(candles){
    const valid=closes(candles).length;
    const vol=annualizedVolatility(candles),mdd=maxDrawdown(candles),score=marketRiskScore(vol,mdd);
    const enoughHistory=valid>=120;
    const metricsOk=finite(vol)&&finite(mdd)&&finite(score);
    const marketVerified=enoughHistory&&metricsOk;
    const critical=marketVerified&&(vol>=80||mdd<=-60);
    return {
      scope:'MARKET_ONLY',
      verified:false,
      marketVerified,
      status:marketVerified?'PARTIAL':'LOCK',
      score:marketVerified?score:null,
      level:marketVerified?classify(score):'UNKNOWN',
      critical,
      metrics:{annualizedVolatility:vol,maxDrawdown:mdd,observations:valid},
      coverage:['volatility','max_drawdown'],
      missing:['liquidity','issuer_fundamental_risk','sanctions_regulatory_risk'],
      items:marketVerified?[
        `Годовая волатильность: ${vol.toFixed(1)}%`,
        `Максимальная просадка: ${mdd.toFixed(1)}%`,
        'Risk layer PARTIAL: учитывает только рыночный риск по истории цены.'
      ]:['Недостаточно истории для подтверждённого market-risk расчёта.'],
      model:'score = 0.5×min(vol/60%,1) + 0.5×min(|MDD|/60%,1); результат ×100',
      gateReason:marketVerified?'Нужны liquidity + issuer + sanctions/regulatory risk для полного verified risk layer.':'Нужно минимум 120 валидных дневных наблюдений.'
    };
  }

  global.InvestorRadarRisk={maxDrawdown,annualizedVolatility,marketRiskScore,classify,assess};
  if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarRisk;
})(typeof window!=='undefined'?window:globalThis);
