// Investor Radar R1.8.23 — Recommendation Engine SBER Completeness Gate
// FACT != ANALYSIS != DECISION. Sanctions alone never imply SELL. SBER active actions require full bank valuation completeness.
(function(global){
  'use strict';
  const ACTIONS=Object.freeze({BUY:'ПОКУПАТЬ',ADD:'ДОБИРАТЬ',HOLD:'ДЕРЖАТЬ',NO_ADD:'НЕ ДОБИРАТЬ',REDUCE:'СОКРАЩАТЬ',SELL:'ПРОДАВАТЬ',WATCH:'НАБЛЮДАТЬ',LOCK:'LOCK'});
  const LIGHT=Object.freeze({GREEN:'ЗЕЛЁНЫЙ',YELLOW:'ЖЁЛТЫЙ',RED:'КРАСНЫЙ',GRAY:'СЕРЫЙ'});
  const finite=x=>Number.isFinite(Number(x));
  const arr=x=>Array.isArray(x)?x:[];

  function dataGate(input){
    const missing=[];
    if(!input||!input.ticker) missing.push('ticker');
    if(!finite(input?.price)) missing.push('current_price');
    if(input?.fundamental?.verified!==true) missing.push('verified_fundamentals');
    if(!finite(input?.fundamental?.growthCagr)) missing.push('fundamental_growth');
    if(input?.valuation?.status!=='PROVISIONAL'&&input?.valuation?.status!=='VERIFIED') missing.push('valuation');
    if(!finite(input?.valuation?.low)||!finite(input?.valuation?.high)) missing.push('valuation_band');
    if(input?.risk?.verified!==true) missing.push('verified_risk');
    if(!finite(input?.risk?.score)) missing.push('risk_score');
    if(String(input?.ticker||'').toUpperCase()==='SBER'){
      const c=input?.valuationCompleteness;
      if(c?.status!=='VERIFIED'||c?.verified!==true) missing.push('sber_full_valuation_completeness');
    }
    const thesisBroken=input?.risk?.thesisBroken===true;
    return {ok:missing.length===0&&!thesisBroken,hardStop:thesisBroken,missing,reason:thesisBroken?'thesis_broken':missing.length?'insufficient_data':'ok'};
  }

  function valuationZone(price,low,high){
    if(!finite(price)||!finite(low)||!finite(high)||low<=0||high<=0||low>high)return 'UNKNOWN';
    if(price<low)return 'ATTRACTIVE'; if(price>high)return 'EXPENSIVE'; return 'FAIR';
  }
  function confidence(input,gate){
    if(!gate.ok)return 'НИЗКАЯ'; let n=0;
    if(input?.valuation?.status==='VERIFIED')n++;
    if(finite(input?.hiddenValue?.gap))n++;
    if(input?.risk?.verified===true&&finite(input?.risk?.score))n++;
    if(arr(input?.facts).length>=2)n++;
    return n>=3?'ВЫСОКАЯ':'СРЕДНЯЯ';
  }
  function decide(input){
    const gate=dataGate(input),ticker=input?.ticker||'—',held=input?.portfolio?.held===true;
    if(gate.hardStop){
      return {ticker,light:LIGHT.RED,action:held?ACTIONS.SELL:ACTIONS.WATCH,confidence:'СРЕДНЯЯ',valuation:'НЕ ОПРЕДЕЛЕНА',why:['Подтверждено разрушение инвестиционного тезиса.'],facts:arr(input?.facts),risks:arr(input?.risk?.items),trigger:'Повторная проверка тезиса после изменения критического фундаментального риска.',gate};
    }
    if(!gate.ok){
      const sberBlocked=gate.missing.includes('sber_full_valuation_completeness');
      return {ticker,light:LIGHT.GRAY,action:ACTIONS.WATCH,confidence:'НИЗКАЯ',valuation:'НЕ ОПРЕДЕЛЕНА',why:['Недостаточно данных для обоснованного вывода.',sberBlocked?'Для SBER не пройден полный bank valuation gate: P/E + P/B + bank quality + common equity/share basis должны быть VERIFIED.':'Не пройдены критические data gates: '+gate.missing.join(', ')+'.'],facts:arr(input?.facts),risks:arr(input?.risk?.items),trigger:'Появление недостающих подтверждённых данных.',gate};
    }
    const zone=valuationZone(+input.price,+input.valuation.low,+input.valuation.high),growth=+input.fundamental.growthCagr,riskScore=+input.risk.score;
    const sanctionsHigh=input?.risk?.sanctions?.verified===true&&input?.risk?.sanctions?.level==='HIGH';
    let action=ACTIONS.WATCH,light=LIGHT.YELLOW,why=[];
    if(sanctionsHigh){
      action=held?ACTIONS.NO_ADD:ACTIONS.WATCH; light=LIGHT.YELLOW;
      why.push('Высокий подтверждённый санкционный/регуляторный риск ограничивает активное увеличение позиции, но сам по себе не является основанием для продажи.');
    }else if(input?.valuation?.status!=='VERIFIED'){
      action=ACTIONS.WATCH; light=LIGHT.YELLOW; why.push('Оценка PROVISIONAL: активное инвестиционное действие заблокировано до verified valuation.');
    }else if(riskScore>=75){
      action=held?ACTIONS.NO_ADD:ACTIONS.WATCH; light=LIGHT.RED; why.push('Риск высокий относительно ожидаемой доходности.');
    }else if(zone==='ATTRACTIVE'&&growth>0){
      action=held?ACTIONS.ADD:ACTIONS.BUY; light=LIGHT.GREEN; why.push('Verified valuation привлекательна при положительной фундаментальной динамике и приемлемом риске.');
    }else if(zone==='FAIR'&&growth>0){
      action=held?ACTIONS.HOLD:ACTIONS.WATCH; light=LIGHT.GREEN; why.push('Verified valuation находится в справедливом диапазоне, фундаментальная динамика положительная.');
    }else if(zone==='EXPENSIVE'&&growth>0){
      action=held?ACTIONS.NO_ADD:ACTIONS.WATCH; light=LIGHT.YELLOW; why.push('Бизнес растёт, но verified valuation указывает на дорогую оценку.');
    }else if(growth<0&&zone==='EXPENSIVE'){
      action=held?ACTIONS.REDUCE:ACTIONS.WATCH; light=LIGHT.RED; why.push('Отрицательная фундаментальная динамика сочетается с дорогой verified valuation.');
    }else{why.push('Сигналы смешанные; ожидаемая доходность не оправдывает активное действие.');}
    return {ticker,light,action,confidence:confidence(input,gate),valuation:zone==='ATTRACTIVE'?'ПРИВЛЕКАТЕЛЬНО':zone==='FAIR'?'СПРАВЕДЛИВО':zone==='EXPENSIVE'?'ДОРОГО':'НЕ ОПРЕДЕЛЕНА',why,facts:arr(input.facts),risks:arr(input?.risk?.items),trigger:input?.trigger||'Изменение фундаментального тренда, оценки или ключевого риска.',gate,diagnostics:{zone,growthCagr:growth,riskScore,sanctionsHigh,held}};
  }
  global.InvestorRadarRecommendation={ACTIONS,LIGHT,dataGate,valuationZone,decide};
  if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarRecommendation;
})(typeof window!=='undefined'?window:globalThis);
