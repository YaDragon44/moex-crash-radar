// R1.8.35 End-to-End Decision Integrity Gate
// Synthetic market/regulatory fixtures are used only to exercise the decision chain.
// Production issuer provenance comes from issuer-risk-registry.js.
const assert=require('assert');
const Registry=require('./issuer-risk-registry.js');
const Risk=require('./risk-layer.js');
const Rec=require('./recommendation-engine.js');

const candles=Array.from({length:130},(_,i)=>({close:100+(i%5)*0.1}));
const liquidity={verified:true,turnoverRub:1e9,numTrades:10000};
const syntheticRegulatoryClear={verified:true,material:false,designated:false,level:'LOW',status:'CLEAR',items:['Synthetic CI fixture only.']};

function integratedRisk(ticker){
  const row=Registry.get(ticker);
  const audit=Registry.audit(ticker);
  assert.equal(audit.riskVerified,true,`${ticker} registry issuer risk must be verified`);
  assert.equal(audit.sectorGateOk,true,`${ticker} sector gate binding must be valid`);
  const issuer={
    ...row.issuer,
    provenanceVerified:audit.riskVerified&&audit.sectorGateOk,
    expectedGate:audit.expectedGate
  };
  const risk=Risk.assess(candles,liquidity,issuer,syntheticRegulatoryClear);
  assert.equal(risk.verified,true,`${ticker} integrated risk should verify under complete synthetic CI inputs`);
  assert.equal(risk.issuerProvenance.verified,true);
  assert.equal(risk.issuerProvenance.derivedBy,audit.expectedGate);
  return risk;
}

function decisionInput(ticker,held=false){
  const input={
    ticker,
    price:90,
    fundamental:{verified:true,growthCagr:10},
    valuation:{status:'VERIFIED',low:100,high:120},
    risk:integratedRisk(ticker),
    portfolio:{held},
    facts:['E2E fixture fact 1','E2E fixture fact 2'],
    trigger:'E2E fixture trigger'
  };
  if(ticker==='SBER') input.valuationCompleteness={status:'VERIFIED',verified:true};
  return input;
}

for(const ticker of ['SBER','X5','MOEX','YDEX']){
  let input=decisionInput(ticker,false);
  let d=Rec.decide(input);
  assert.equal(d.gate.issuerProvenance.ok,true,`${ticker} provenance must pass`);
  assert.equal(d.action,'ПОКУПАТЬ',`${ticker} intact chain should allow BUY in positive synthetic fixture`);

  // Manual derivedBy substitution must fail closed even when risk.verified remains true.
  input=decisionInput(ticker,false);
  input.risk.issuerProvenance={verified:true,derivedBy:'MANUAL_OVERRIDE'};
  input.risk.verified=true;
  d=Rec.decide(input);
  assert.equal(d.action,'НАБЛЮДАТЬ',`${ticker} forged sector provenance must WATCH`);
  assert.equal(d.light,'СЕРЫЙ');
  assert(d.gate.missing.includes('issuer_sector_gate_mismatch'));

  // Removing provenance must fail closed.
  input=decisionInput(ticker,false);
  delete input.risk.issuerProvenance;
  input.risk.verified=true;
  d=Rec.decide(input);
  assert.equal(d.action,'НАБЛЮДАТЬ',`${ticker} missing provenance must WATCH`);
  assert(d.gate.missing.includes('issuer_risk_provenance_missing'));

  // A forged thesisBroken flag without trusted provenance must never become SELL.
  input=decisionInput(ticker,true);
  input.risk.thesisBroken=true;
  input.risk.issuerProvenance={verified:true,derivedBy:'MANUAL_OVERRIDE'};
  input.risk.verified=true;
  d=Rec.decide(input);
  assert.equal(d.action,'НАБЛЮДАТЬ',`${ticker} forged thesisBroken must not SELL`);
  assert.notEqual(d.action,'ПРОДАВАТЬ');
  assert.equal(d.gate.hardStop,false);
}

// Current production sanctions registry remains fail-closed for YDEX/X5 and verified for SBER/MOEX.
const Sanctions=require('./sanctions-regulatory-registry.js');
assert.equal(Sanctions.get('SBER').verified,true);
assert.equal(Sanctions.get('MOEX').verified,true);
assert.equal(Sanctions.get('YDEX').verified,false);
assert.equal(Sanctions.get('X5').verified,false);

console.log('R1.8.35 end-to-end decision integrity gate: PASS');
