const assert=require('assert');
const E=require('./recommendation-engine.js');
function base(){return {ticker:'TEST',price:90,fundamental:{verified:true,growthCagr:12},valuation:{status:'VERIFIED',low:100,high:120},risk:{verified:true,score:40,thesisBroken:false,items:['Тестовый риск'],sanctions:{verified:false,material:false,designated:false,level:'UNKNOWN'}},portfolio:{held:true},facts:['Факт 1','Факт 2'],trigger:'Тестовый триггер'};}
let r=E.decide(base()); assert.equal(r.action,'ДОБИРАТЬ'); assert.equal(r.light,'ЗЕЛЁНЫЙ');
let x=base();x.portfolio.held=false;r=E.decide(x);assert.equal(r.action,'ПОКУПАТЬ');
x=base();x.valuation.status='PROVISIONAL';r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.notEqual(r.action,'ДОБИРАТЬ');

// R1.8.31: only VERIFIED + MATERIAL + HIGH sanctions risk limits active position increase; it never auto-SELLs.
x=base();x.risk.sanctions={verified:true,material:true,designated:true,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'НЕ ДОБИРАТЬ');assert.notEqual(r.action,'ПРОДАВАТЬ');assert.equal(r.light,'ЖЁЛТЫЙ');assert.equal(r.diagnostics.sanctionsMaterialHigh,true);assert.equal(r.diagnostics.sanctionsDesignated,true);
x=base();x.portfolio.held=false;x.risk.sanctions={verified:true,material:true,designated:true,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.notEqual(r.action,'ПРОДАВАТЬ');
// HIGH without explicit material=true must not be silently treated as material sanctions risk.
x=base();x.risk.sanctions={verified:true,material:false,designated:false,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'ДОБИРАТЬ');assert.equal(r.diagnostics.sanctionsMaterialHigh,false);

x=base();x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'ПРОДАВАТЬ');assert.equal(r.light,'КРАСНЫЙ');assert.equal(r.gate.hardStop,true);
x=base();x.portfolio.held=false;x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'КРАСНЫЙ');
x=base();delete x.valuation.low;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('valuation_band'));
x=base();x.risk={thesisBroken:false};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('verified_risk'));assert(r.gate.missing.includes('risk_score'));

// R1.8.23: SBER must not receive active recommendation until full bank valuation completeness is VERIFIED.
x=base();x.ticker='SBER';r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'СЕРЫЙ');assert.equal(r.confidence,'НИЗКАЯ');assert(r.gate.missing.includes('sber_full_valuation_completeness'));assert.equal(r.valuation,'НЕ ОПРЕДЕЛЕНА');
x=base();x.ticker='SBER';x.valuationCompleteness={status:'PARTIAL',verified:false};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('sber_full_valuation_completeness'));
x=base();x.ticker='SBER';x.valuationCompleteness={status:'VERIFIED',verified:true};r=E.decide(x);assert.equal(r.action,'ДОБИРАТЬ');assert.equal(r.light,'ЗЕЛЁНЫЙ');assert(!r.gate.missing.includes('sber_full_valuation_completeness'));
x=base();x.ticker='SBER';x.portfolio.held=false;x.valuationCompleteness={status:'VERIFIED',verified:true};r=E.decide(x);assert.equal(r.action,'ПОКУПАТЬ');

// R1.8.24: portfolio context must be explicit. Missing/invalid held must never be treated as held=false.
x=base();delete x.portfolio;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'СЕРЫЙ');assert.equal(r.confidence,'НИЗКАЯ');assert(r.gate.missing.includes('portfolio_context'));assert.equal(r.diagnostics,undefined);
x=base();x.portfolio={};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('portfolio_context'));
x=base();x.portfolio={held:'false'};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('portfolio_context'));
x=base();delete x.portfolio;x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'КРАСНЫЙ');assert.equal(r.confidence,'НИЗКАЯ');assert.notEqual(r.action,'ПРОДАВАТЬ');assert(r.gate.missing.includes('portfolio_context'));

assert.equal(E.valuationZone(99,100,120),'ATTRACTIVE');assert.equal(E.valuationZone(110,100,120),'FAIR');assert.equal(E.valuationZone(121,100,120),'EXPENSIVE');
console.log('R1.8.31 recommendation + portfolio + sanctions semantics tests: PASS');
