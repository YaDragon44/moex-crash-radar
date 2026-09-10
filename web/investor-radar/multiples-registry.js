// Investor Radar R1.8.8 — Verified Multiples Registry Foundation
// No multiple is considered verified without reproducible inputs + source/asOf metadata.
(function(global){
'use strict';
const REGISTRY={
 SBER:{status:'LOCK',asOf:null,source:null,historicalPE:[],peerPE:[],peers:[],missing:['verified_eps','historical_pe_3plus','peer_pe_2plus','source_metadata'],note:'Недостаточно данных для обоснованного вывода.'},
 YDEX:{status:'LOCK',asOf:null,source:null,historicalPE:[],peerPE:[],peers:[],missing:['historical_pe_3plus','peer_pe_2plus','source_metadata'],note:'EPS есть в фундаментальном реестре, но исторический и peer P/E пока не подтверждены воспроизводимым расчётом.'},
 X5:{status:'LOCK',asOf:null,source:null,historicalPE:[],peerPE:[],peers:[],missing:['verified_eps','historical_pe_3plus','peer_pe_2plus','source_metadata'],note:'Нет полного набора подтверждённых EPS и P/E для VERIFIED valuation.'},
 MOEX:{status:'LOCK',asOf:null,source:null,historicalPE:[],peerPE:[],peers:[],missing:['historical_pe_3plus','peer_pe_2plus','source_metadata'],note:'EPS есть в фундаментальном реестре, но исторический и peer P/E пока не подтверждены воспроизводимым расчётом.'}
};
function get(t){return REGISTRY[t]||{status:'LOCK',asOf:null,source:null,historicalPE:[],peerPE:[],peers:[],missing:['registry_entry'],note:'Нет записи в verified multiples registry.'};}
function isVerified(x){return x?.status==='VERIFIED'&&Array.isArray(x.historicalPE)&&x.historicalPE.length>=3&&Array.isArray(x.peerPE)&&x.peerPE.length>=2&&!!x.source&&!!x.asOf;}
global.InvestorRadarMultiples={REGISTRY,get,isVerified};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarMultiples;
})(typeof window!=='undefined'?window:globalThis);
