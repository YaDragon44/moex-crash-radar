const assert=require('assert');
const E=require('./recommendation-engine.js');
function base(){return {ticker:'TEST',price:90,fundamental:{verified:true,growthCagr:12},valuation:{status:'VERIFIED',low:100,high:120},risk:{verified:true,score:40,thesisBroken:false,items:['Тестовый риск'],issuerProvenance:{verified:true,derivedBy:'TEST_SECTOR_GATE'},sanctions:{verified:false,material:false,designated:false,level:'UNKNOWN'}},portfolio:{held:true},facts:['Факт 1','Факт 2'],trigger:'Тестовый триггер'};}
function sberBase(){const x=base();x.ticker='SBER';x.risk.issuerProvenance={verified:true,derivedBy:'BANK_ISSUER_RISK_GATE_R1.8.28'};return x;}
let r=E.decide(base()); assert.equal(r.action,'ДОБИРАТЬ'); assert.equal(r.light,'ЗЕЛЁНЫЙ');
let x=base();x.portfolio.held=false;r=E.decide(x);assert.equal(r.action,'ПОКУПАТЬ');
x=base();x.valuation.status='PROVISIONAL';r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.notEqual(r.action,'ДОБИРАТЬ');

// R1.8.31 sanctions semantics.
x=base();x.risk.sanctions={verified:true,material:true,designated:true,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'НЕ ДОБИРАТЬ');assert.notEqual(r.action,'ПРОДАВАТЬ');assert.equal(r.light,'ЖЁЛТЫЙ');assert.equal(r.diagnostics.sanctionsMaterialHigh,true);assert.equal(r.diagnostics.sanctionsDesignated,true);
x=base();x.portfolio.held=false;x.risk.sanctions={verified:true,material:true,designated:true,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.notEqual(r.action,'ПРОДАВАТЬ');
x=base();x.risk.sanctions={verified:true,material:false,designated:false,level:'HIGH'};r=E.decide(x);assert.equal(r.action,'ДОБИРАТЬ');assert.equal(r.diagnostics.sanctionsMaterialHigh,false);

x=base();x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'ПРОДАВАТЬ');assert.equal(r.light,'КРАСНЫЙ');assert.equal(r.gate.hardStop,true);
x=base();x.portfolio.held=false;x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'КРАСНЫЙ');
x=base();delete x.valuation.low;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('valuation_band'));
x=base();x.risk={thesisBroken:false};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('verified_risk'));assert(r.gate.missing.includes('risk_score'));assert(r.gate.missing.includes('issuer_risk_provenance_missing'));

// R1.8.23 SBER valuation completeness.
x=sberBase();r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'СЕРЫЙ');assert.equal(r.confidence,'НИЗКАЯ');assert(r.gate.missing.includes('sber_full_valuation_completeness'));assert.equal(r.valuation,'НЕ ОПРЕДЕЛЕНА');
x=sberBase();x.valuationCompleteness={status:'PARTIAL',verified:false};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('sber_full_valuation_completeness'));
x=sberBase();x.valuationCompleteness={status:'VERIFIED',verified:true};r=E.decide(x);assert.equal(r.action,'ДОБИРАТЬ');assert.equal(r.light,'ЗЕЛЁНЫЙ');assert(!r.gate.missing.includes('sber_full_valuation_completeness'));
x=sberBase();x.portfolio.held=false;x.valuationCompleteness={status:'VERIFIED',verified:true};r=E.decide(x);assert.equal(r.action,'ПОКУПАТЬ');

// R1.8.24 explicit portfolio context.
x=base();delete x.portfolio;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'СЕРЫЙ');assert.equal(r.confidence,'НИЗКАЯ');assert(r.gate.missing.includes('portfolio_context'));assert.equal(r.diagnostics,undefined);
x=base();x.portfolio={};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('portfolio_context'));
x=base();x.portfolio={held:'false'};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('portfolio_context'));
x=base();delete x.portfolio;x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'КРАСНЫЙ');assert.equal(r.confidence,'НИЗКАЯ');assert.notEqual(r.action,'ПРОДАВАТЬ');assert(r.gate.missing.includes('portfolio_context'));

// R1.8.34: manual risk.verified cannot bypass exact sector provenance.
x=base();delete x.risk.issuerProvenance;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.light,'СЕРЫЙ');assert(r.gate.missing.includes('issuer_risk_provenance_missing'));
x=sberBase();x.valuationCompleteness={status:'VERIFIED',verified:true};x.risk.issuerProvenance={verified:true,derivedBy:'FAKE_GATE'};r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert(r.gate.missing.includes('issuer_sector_gate_mismatch'));
x=base();delete x.risk.issuerProvenance;x.risk.thesisBroken=true;r=E.decide(x);assert.equal(r.action,'НАБЛЮДАТЬ');assert.equal(r.gate.hardStop,false);assert.notEqual(r.action,'ПРОДАВАТЬ');

assert.equal(E.valuationZone(99,100,120),'ATTRACTIVE');assert.equal(E.valuationZone(110,100,120),'FAIR');assert.equal(E.valuationZone(121,100,120),'EXPENSIVE');
console.log('R1.8.34 recommendation + issuer provenance + portfolio + sanctions tests: PASS');
