// Investor Radar R1.8.16 — SBER Valuation Input Registry
// Facts only. Market prices remain runtime MOEX inputs; no guessed historical closes.
(function(global){
'use strict';
const SBER={
 ticker:'SBER',sector:'BANKS',
 epsSeries:[
  {year:2023,eps:69.10,verified:true,source:'MOEX issuer financials / Sber disclosure',asOf:'2023-12-31'},
  {year:2024,eps:72.03,verified:true,source:'MOEX issuer financials / Sber disclosure',asOf:'2024-12-31'},
  {year:2025,eps:77.81,verified:true,source:'MOEX issuer financials / Sber disclosure',asOf:'2025-12-31'}
 ],
 capitalSeries:[
  {year:2023,capitalBnRub:6692.3,verified:true,source:'MOEX issuer financials / Sber disclosure',asOf:'2023-12-31'},
  {year:2024,capitalBnRub:7317.4,verified:true,source:'MOEX issuer financials / Sber disclosure',asOf:'2024-12-31'},
  {year:2025,capitalBnRub:7942.8,verified:true,source:'MOEX issuer financials / Sber disclosure',asOf:'2025-12-31'}
 ],
 bankMetrics:{
  2023:{roe:25.3,cet1:11.6,npl:3.4,costOfRisk:0.76},
  2024:{roe:24.0,cet1:11.8,npl:3.7,costOfRisk:0.98},
  2025:{roe:22.7,cet1:12.3,npl:4.9,costOfRisk:1.30}
 },
 peers:['VTBR','T'],
 source:'https://www.moex.com/en/stocks/sber',
 methodology:'Historical P/E = last available MOEX close in fiscal year / verified EPS. P/B requires verified equity attributable/share basis; total capital is stored but is NOT silently treated as common BVPS. Peer P/E requires verified positive EPS and MOEX price.'
};
function audit(){
 const epsOk=SBER.epsSeries.length>=3&&SBER.epsSeries.every(x=>x.verified===true&&Number(x.eps)>0&&x.source&&x.asOf);
 const capitalOk=SBER.capitalSeries.length>=3&&SBER.capitalSeries.every(x=>x.verified===true&&Number(x.capitalBnRub)>0&&x.source&&x.asOf);
 const bankOk=[2023,2024,2025].every(y=>['roe','cet1','npl','costOfRisk'].every(k=>Number.isFinite(SBER.bankMetrics[y]?.[k])));
 return {status:epsOk&&capitalOk&&bankOk?'VERIFIED_INPUT':'LOCK',epsOk,capitalOk,bankOk,historicalPriceGate:'RUNTIME_MOEX_REQUIRED',peerPriceGate:'RUNTIME_MOEX_REQUIRED',bookValuePerShareGate:'ATTRIBUTABLE_EQUITY_AND_SHARE_BASIS_REQUIRED',bankValuationGate:'PB_ROE_REQUIRED'};
}
global.InvestorRadarSberValuation={SBER,audit};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberValuation;
})(typeof window!=='undefined'?window:globalThis);
