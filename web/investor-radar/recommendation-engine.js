// Investor Radar R1.8.34 — Recommendation Engine Issuer Provenance Hardening
// FACT != ANALYSIS != DECISION. Active actions require explicit portfolio context and reproducible sector-gated issuer risk.
// Sanctions material/designated risk is separate from issuer thesisBroken and never creates an automatic SELL.
(function(global){
  'use strict';
  const ACTIONS=Object.freeze({BUY:'ПОКУПАТЬ',ADD:'ДОБИРАТЬ',HOLD:'ДЕРЖАТЬ',NO_ADD:'НЕ ДОБИРАТЬ',REDUCE:'СОКРАЩАТЬ',SELL:'ПРОДАВАТЬ',WATCH:'НАБЛЮДАТЬ',LOCK:'LOCK'});
  const LIGHT=Object.freeze({GREEN:'ЗЕЛЁНЫЙ',YELLOW:'ЖЁЛТЫЙ',RED:'КРАСНЫЙ',GRAY:'СЕРЫЙ'});
  const ISSUER_GATES=Object.freeze({YDEX:'TECH_ISSUER_RISK_GATE_R1.8.32',X5:'RETAIL_ISSUER_RISK_GATE_R1.8.29',MOEX:'EXCHANGE_ISSUER_RISK_GATE_R1.8.30',SBER:'BANK_ISSUER_RISK_GATE_R1.8.28'});
  const finite=x=>Number.isFinite(Number(x));
  const arr=x=>Array.isArray(x)?x:[];
  const portfolioKnown=input=>typeof input?.portfolio?.held==='boolean';
  function provenanceGate(input){
    const ticker=String(input?.ticker||'').toUpperCase(),p=input?.risk?.issuerProvenance||{},expected=ISSUER_GATES[ticker]||null;
    if(p?.verified!==true)return {ok:false,reason:'issuer_risk_provenance_missing',expected,derivedBy:p?.derivedBy||null};
    if(expected&&p?.derivedBy!==expected)return {ok:false,reason:'issuer_sector_gate_mismatch',expected,derivedBy:p?.derivedBy||null};
    return {ok:true,reason:'ok',expected,derivedBy:p?.derivedBy||null};
  }
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
    const pg=provenanceGate(input); if(!pg.ok) missing.push(pg.reason);
    if(!portfolioKnown(input)) missing.push('portfolio_context');
    if(String(input?.ticker||'').toUpperCase()==='SBER'){
      const c=input?.valuationCompleteness;
      if(c?.status!=='VERIFIED'||c?.verified!==true) missing.push('sber_full_valuation_completeness');
    }
    const thesisBrokenTrusted=pg.ok&&input?.risk?.thesisBroken===true;
    return {ok:missing.length===0&&!thesisBrokenTrusted,hardStop:thesisBrokenTrusted,missing,reason:thesisBrokenTrusted?'thesis_broken':missing.length?'insufficient_data':'ok',issuerProvenance:pg};
  }
  function valuationZone(price,low,high){if(!finite(price)||!finite(low)||!finite(high)||low<=0||high<=0||low>high)return 'UNKNOWN';if(price<low)return 'ATTRACTIVE';if(price>high)return 'EXPENSIVE';return 'FAIR';}
  function confidence(input,gate){if(!gate.ok)return 'НИЗКАЯ';let n=0;if(input?.valuation?.status==='VERIFIED')n++;if(finite(input?.hiddenValue?.gap))n++;if(input?.risk?.verified===true&&finite(input?.risk?.score)&&gate?.issuerProvenance?.ok)n++;if(arr(input?.facts).length>=2)n++;return n>=3?'ВЫСОКАЯ':'СРЕДНЯЯ';}
  function decide(input){
    const gate=dataGate(input),ticker=input?.ticker||'—',known=portfolioKnown(input),held=known&&input.portfolio.held===true;
    if(gate.hardStop){return {ticker,light:LIGHT.RED,action:known&&held?ACTIONS.SELL:ACTIONS.WATCH,confidence:known?'СРЕДНЯЯ':'НИЗКАЯ',valuation:'НЕ ОПРЕДЕЛЕНА',why:[known?'Подтверждено разрушение инвестиционного тезиса секторно-верифицированным issuer-risk gate.':'Подтверждено разрушение инвестиционного тезиса, но статус позиции в портфеле не подтверждён.'],facts:arr(input?.facts),risks:arr(input?.risk?.items),trigger:known?'Повторная проверка тезиса после изменения критического фундаментального риска.':'Подтвердить наличие позиции; без portfolio.held=true продажа не рекомендуется.',gate};}
    if(!gate.ok){
      const sberBlocked=gate.missing.includes('sber_full_valuation_completeness');
      const portfolioBlocked=gate.missing.includes('portfolio_context');
      const provenanceBlocked=gate.missing.includes('issuer_risk_provenance_missing')||gate.missing.includes('issuer_sector_gate_mismatch');
      const detail=provenanceBlocked?'Issuer-risk не имеет подтверждённого секторного provenance: активная рекомендация заблокирована.':sberBlocked?'Для SBER не пройден полный bank valuation gate: P/E + P/B + bank quality + common equity/share basis должны быть VERIFIED.':portfolioBlocked?'Не подтверждён статус позиции: portfolio.held должен быть явно true или false; BUY/ADD/HOLD/REDUCE/SELL без этого заблокированы.':'Не пройдены критические data gates: '+gate.missing.join(', ')+'.';
      return {ticker,light:LIGHT.GRAY,action:ACTIONS.WATCH,confidence:'НИЗКАЯ',valuation:'НЕ ОПРЕДЕЛЕНА',why:['Недостаточно данных для обоснованного вывода.',detail],facts:arr(input?.facts),risks:arr(input?.risk?.items),trigger:'Появление недостающих подтверждённых данных.',gate};
    }
    const zone=valuationZone(+input.price,+input.valuation.low,+input.valuation.high),growth=+input.fundamental.growthCagr,riskScore=+input.risk.score;
    const sanctions=input?.risk?.sanctions||{};
    const sanctionsMaterialHigh=sanctions.verified===true&&sanctions.material===true&&sanctions.level==='HIGH';
    const sanctionsDesignated=sanctions.verified===true&&sanctions.designated===true;
    let action=ACTIONS.WATCH,light=LIGHT.YELLOW,why=[];
    if(sanctionsMaterialHigh){action=held?ACTIONS.NO_ADD:ACTIONS.WATCH;light=LIGHT.YELLOW;why.push('Высокий подтверждённый материальный санкционный/регуляторный риск ограничивает активное увеличение позиции, но сам по себе не является основанием для продажи.');}
    else if(input?.valuation?.status!=='VERIFIED'){action=ACTIONS.WATCH;light=LIGHT.YELLOW;why.push('Оценка PROVISIONAL: активное инвестиционное действие заблокировано до verified valuation.');}
    else if(riskScore>=75){action=held?ACTIONS.NO_ADD:ACTIONS.WATCH;light=LIGHT.RED;why.push('Риск высокий относительно ожидаемой доходности.');}
    else if(zone==='ATTRACTIVE'&&growth>0){action=held?ACTIONS.ADD:ACTIONS.BUY;light=LIGHT.GREEN;why.push('Verified valuation привлекательна при положительной фундаментальной динамике и приемлемом риске.');}
    else if(zone==='FAIR'&&growth>0){action=held?ACTIONS.HOLD:ACTIONS.WATCH;light=LIGHT.GREEN;why.push('Verified valuation находится в справедливом диапазоне, фундаментальная динамика положительная.');}
    else if(zone==='EXPENSIVE'&&growth>0){action=held?ACTIONS.NO_ADD:ACTIONS.WATCH;light=LIGHT.YELLOW;why.push('Бизнес растёт, но verified valuation указывает на дорогую оценку.');}
    else if(growth<0&&zone==='EXPENSIVE'){action=held?ACTIONS.REDUCE:ACTIONS.WATCH;light=LIGHT.RED;why.push('Отрицательная фундаментальная динамика сочетается с дорогой verified valuation.');}
    else{why.push('Сигналы смешанные; ожидаемая доходность не оправдывает активное действие.');}
    return {ticker,light,action,confidence:confidence(input,gate),valuation:zone==='ATTRACTIVE'?'ПРИВЛЕКАТЕЛЬНО':zone==='FAIR'?'СПРАВЕДЛИВО':zone==='EXPENSIVE'?'ДОРОГО':'НЕ ОПРЕДЕЛЕНА',why,facts:arr(input.facts),risks:arr(input?.risk?.items),trigger:input?.trigger||'Изменение фундаментального тренда, оценки или ключевого риска.',gate,diagnostics:{zone,growthCagr:growth,riskScore,sanctionsMaterialHigh,sanctionsDesignated,portfolioKnown:known,held,issuerProvenance:gate.issuerProvenance}};
  }
  global.InvestorRadarRecommendation={ACTIONS,LIGHT,ISSUER_GATES,provenanceGate,dataGate,valuationZone,decide};
  if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarRecommendation;
})(typeof window!=='undefined'?window:globalThis);
