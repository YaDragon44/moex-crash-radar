const assert=require('assert');
const E=require('./recommendation-engine.js');
function base(){return {ticker:'TEST',price:90,fundamental:{verified:true,growthCagr:12},valuation:{status:'VERIFIED',low:100,high:120},risk:{verified:true,score:40,thesisBroken:false,items:['Тестовый риск'],sanctions:{verified:false,level:'UNKNOWN'}},portfolio:{held:true},facts:['Факт 1','Факт 2'],trigger:'Тестовый триггер'};}
let r=E.decide(base()); assert.equal(r.action,'ДОБИРАТЬ'); assert.equal(r.light,'ЗЕЛЁНЫЙ');
let x=base();x.portfolio.held=false;r=E.decide(x);assert.equal(r.action,'ПОКУПАТЬ');
x=base();x.valuation.status='PROVISIONAL';r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.notEqual(r.action,'ДОБИРАТЬ');
x=base();x.risk.sanctions={verified:true,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'НЕ ДОБИРАТЬ');assert.notEqual(r.action,'ПРОДАВАТЬ');assert.equal(r.light,'ЖЁЛТЫЙ');
x=base();x.portfolio.held=false;x.risk.sanctions={verified:true,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.notEqual(r.action,'ПРОДАВАТЬ');
x=base();x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'ПРОДАВАТЬ');assert.equal(r.light,'КРАСНЫЙ');assert.equal(r.gate.hardStop,true);
x=base();x.portfolio.held=false;x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'КРАСНЫЙ');
x=base();delete x.valuation.low;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('valuation_band'));
x=base();x.risk={thesisBroken:false};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('verified_risk'));assert(r.gate.missing.includes('risk_score'));
assert.equal(E.valuationZone(99,100,120),'ATTRACTIVE');assert.equal(E.valuationZone(110,100,120),'FAIR');assert.equal(E.valuationZone(121,100,120),'EXPENSIVE');
console.log('R1.8.5.1 recommendation safety tests: PASS');
