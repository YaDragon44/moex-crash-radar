const assert=require('assert');
const E=require('./recommendation-engine.js');

function base(){return {
 ticker:'TEST', price:90,
 fundamental:{verified:true,growthCagr:12},
 valuation:{status:'PROVISIONAL',low:100,high:120},
 hiddenValue:{gap:4},
 risk:{verified:true,score:40,critical:false,items:['Тестовый риск']},
 facts:['Факт 1','Факт 2'], trigger:'Тестовый триггер'
};}

let r=E.decide(base());
assert.equal(r.action,'ДОБИРАТЬ');
assert.equal(r.light,'ЗЕЛЁНЫЙ');
assert.equal(r.valuation,'ПРИВЛЕКАТЕЛЬНО');

let x=base(); x.price=110; r=E.decide(x);
assert.equal(r.action,'ДЕРЖАТЬ');
assert.equal(r.valuation,'СПРАВЕДЛИВО');

x=base(); x.price=130; r=E.decide(x);
assert.equal(r.action,'НЕ ДОБИРАТЬ');
assert.equal(r.valuation,'ДОРОГО');

x=base(); x.fundamental.growthCagr=-5; x.price=130; r=E.decide(x);
assert.equal(r.action,'СОКРАЩАТЬ');
assert.equal(r.light,'КРАСНЫЙ');

x=base(); delete x.valuation.low; r=E.decide(x);
assert.equal(r.action,'НАБЛЮДАТЬ');
assert.equal(r.light,'СЕРЫЙ');
assert(r.gate.missing.includes('valuation_band'));

x=base(); x.risk={critical:false}; r=E.decide(x);
assert.equal(r.action,'НАБЛЮДАТЬ');
assert.equal(r.light,'СЕРЫЙ');
assert(r.gate.missing.includes('verified_risk'));
assert(r.gate.missing.includes('risk_score'));

x=base(); x.risk.critical=true; r=E.decide(x);
assert.equal(r.action,'ПРОДАВАТЬ');
assert.equal(r.light,'КРАСНЫЙ');
assert.equal(r.gate.hardStop,true);

assert.equal(E.valuationZone(99,100,120),'ATTRACTIVE');
assert.equal(E.valuationZone(110,100,120),'FAIR');
assert.equal(E.valuationZone(121,100,120),'EXPENSIVE');

console.log('R1.8.1 recommendation engine tests: PASS');
