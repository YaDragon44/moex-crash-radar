// Investor Radar R1.8.1 — Recommendation Engine
// FACT != ANALYSIS != DECISION. Missing critical data => НАБЛЮДАТЬ.
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
    if(input?.risk?.critical===true) return {ok:false,hardStop:true,missing,reason:'critical_risk'};
    return {ok:missing.length===0,hardStop:false,missing,reason:missing.length?'insufficient_data':'ok'};
  }

  function valuationZone(price,low,high){
    if(!finite(price)||!finite(low)||!finite(high)||low<=0||high<=0||low>high) return 'UNKNOWN';
    if(price<low) return 'ATTRACTIVE';
    if(price>high) return 'EXPENSIVE';
    return 'FAIR';
  }

  function confidence(input,gate){
    if(!gate.ok) return 'НИЗКАЯ';
    let n=0;
    if(input?.valuation?.status==='VERIFIED') n++;
    if(finite(input?.hiddenValue?.gap)) n++;
    if(input?.risk?.verified===true&&finite(input?.risk?.score)) n++;
    if(arr(input?.facts).length>=2) n++;
    return n>=3?'ВЫСОКАЯ':'СРЕДНЯЯ';
  }

  function decide(input){
    const gate=dataGate(input);
    const ticker=input?.ticker||'—';
    if(gate.hardStop){
      return {ticker,light:LIGHT.RED,action:ACTIONS.SELL,confidence:'СРЕДНЯЯ',valuation:'НЕ ОПРЕДЕЛЕНА',why:['Сработал критический риск-gate.'],facts:arr(input?.facts),risks:arr(input?.risk?.items),trigger:'Пересмотр после снятия/переоценки критического риска.',gate};
    }
    if(!gate.ok){
      return {ticker,light:LIGHT.GRAY,action:ACTIONS.WATCH,confidence:'НИЗКАЯ',valuation:'НЕ ОПРЕДЕЛЕНА',why:['Недостаточно данных для обоснованного вывода.','Не пройдены критические data gates: '+gate.missing.join(', ')+'.'],facts:arr(input?.facts),risks:arr(input?.risk?.items),trigger:'Появление недостающих подтверждённых данных.',gate};
    }

    const zone=valuationZone(Number(input.price),Number(input.valuation.low),Number(input.valuation.high));
    const growth=Number(input.fundamental.growthCagr);
    const gap=finite(input?.hiddenValue?.gap)?Number(input.hiddenValue.gap):null;
    const riskScore=Number(input.risk.score);
    let action=ACTIONS.HOLD,light=LIGHT.YELLOW,why=[];

    if(riskScore>=75){
      action=ACTIONS.NO_ADD;light=LIGHT.RED;why.push('Риск высокий относительно ожидаемой доходности.');
    }else if(zone==='ATTRACTIVE'&&growth>0&&(gap===null||gap>=0)){
      action=ACTIONS.ADD;light=LIGHT.GREEN;why.push('Цена ниже модельного диапазона при положительной фундаментальной динамике.');
    }else if(zone==='FAIR'&&growth>0){
      action=ACTIONS.HOLD;light=LIGHT.GREEN;why.push('Оценка находится в модельном справедливом диапазоне, фундаментальная динамика положительная.');
    }else if(zone==='EXPENSIVE'&&growth>0){
      action=ACTIONS.NO_ADD;light=LIGHT.YELLOW;why.push('Бизнес растёт, но цена выше модельного диапазона.');
    }else if(growth<0&&zone==='EXPENSIVE'){
      action=ACTIONS.REDUCE;light=LIGHT.RED;why.push('Отрицательная фундаментальная динамика сочетается с дорогой оценкой.');
    }else{
      action=ACTIONS.WATCH;light=LIGHT.YELLOW;why.push('Сигналы смешанные; ожидаемая доходность не выглядит достаточно очевидной для активного действия.');
    }

    return {ticker,light,action,confidence:confidence(input,gate),valuation:zone==='ATTRACTIVE'?'ПРИВЛЕКАТЕЛЬНО':zone==='FAIR'?'СПРАВЕДЛИВО':zone==='EXPENSIVE'?'ДОРОГО':'НЕ ОПРЕДЕЛЕНА',why,facts:arr(input.facts),risks:arr(input?.risk?.items),trigger:input?.trigger||'Изменение фундаментального тренда, оценки или ключевого риска.',gate,diagnostics:{zone,growthCagr:growth,hiddenValueGap:gap,riskScore}};
  }

  global.InvestorRadarRecommendation={ACTIONS,LIGHT,dataGate,valuationZone,decide};
  if(typeof module!=='undefined'&&module.exports) module.exports=global.InvestorRadarRecommendation;
})(typeof window!=='undefined'?window:globalThis);
