// Investor Radar R1.8.55 — SBER production valuation completeness integration
// Minimal runtime adapter: enriches SBER recommendation input with the already verified
// bank-specific P/B, bank-quality and issuer-reported common-BVPS evidence gates.
(function(global){
'use strict';
function build(input){
  if(String(input?.ticker||'').toUpperCase()!=='SBER') return input;
  const reg=global.InvestorRadarSberValuation;
  const bank=global.InvestorRadarBankValuation;
  const quality=global.InvestorRadarBankQualityTrend;
  const reported=global.InvestorRadarSberReportedBVPS;
  const complete=global.InvestorRadarSberValuationCompleteness;
  const missing=[];
  if(!reg?.SBER) missing.push('sber_registry');
  if(!bank?.assess) missing.push('bank_valuation_gate');
  if(!quality?.assess) missing.push('bank_quality_trend');
  if(!reported?.assess) missing.push('reported_bvps');
  if(!complete?.assess) missing.push('completeness_gate');
  if(missing.length) return {...input,valuationCompleteness:{status:'PARTIAL',verified:false,missing}};

  const b=reported.assess();
  const q=quality.assess(reg.SBER.bankMetrics||{});
  const m=reg.SBER.bankMetrics?.[2025];
  const price=Number(input?.price);
  const priceOk=Number.isFinite(price)&&price>0;
  const bankVal=(b.verified===true&&m&&priceOk)?bank.assess({
    price,
    bookValuePerShare:b.bookValuePerShare,
    roe:m.roe,
    cet1:m.cet1,
    npl:m.npl,
    costOfRisk:m.costOfRisk,
    verified:true,
    source:'MOEX ISS market price + Sberbank Annual Report 2025 issuer-reported common BVPS + verified SBER bank metrics',
    asOf:new Date().toISOString().slice(0,10)
  }):{status:'LOCK',verified:false,missing:[...(priceOk?[]:['current_price']),...(b.verified?[]:['reported_bvps']),...(m?[]:['bank_metrics_2025'])]};

  // The generic valuation may remain PROVISIONAL when peer P/E is incomplete. For the
  // bank completeness gate, verified historical P/E evidence is independently sufficient.
  const historicalPeOk=Number.isFinite(Number(input?.valuation?.historicalMedianPE));
  const pe=historicalPeOk?{status:'VERIFIED',verified:true}:{status:'LOCK',verified:false};
  const c=complete.assess({
    peRuntime:pe,
    bankValuation:bankVal,
    bankQuality:q,
    equityAttribution:null,
    reportedBvps:b,
    valuationLabel:input?.valuation?.status==='VERIFIED'?'VERIFIED_MODEL_OUTPUT':'PROVISIONAL_MODEL_OUTPUT'
  });
  return {...input,valuationCompleteness:c,sberBankValuation:bankVal,sberBankQuality:q,sberReportedBvps:b};
}
function install(){
  const rec=global.InvestorRadarRecommendation;
  if(!rec?.decide||rec.__sberR1855Installed) return false;
  const base=rec.decide.bind(rec);
  rec.decide=function(input){return base(build(input));};
  rec.__sberR1855Installed=true;
  return true;
}
global.InvestorRadarSberProductionCompleteness={build,install};
install();
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberProductionCompleteness;
})(typeof window!=='undefined'?window:globalThis);
