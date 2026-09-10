// Investor Radar R1.8.11 — Peer Earnings Registry
// No EPS is verified unless backed by an explicit issuer/financial-statement source and asOf date.
(function(global){
'use strict';
const REGISTRY={
 VTBR:{status:'LOCK',eps:null,verified:false,source:null,asOf:null,note:'Недостаточно проверенных данных для peer P/E.'},
 T:{status:'LOCK',eps:null,verified:false,source:null,asOf:null,note:'Недостаточно проверенных данных для peer P/E.'},
 VKCO:{status:'LOCK',eps:null,verified:false,source:null,asOf:null,note:'P/E неприменим при неположительной/несопоставимой прибыли; требуется актуальная проверка.'},
 OZON:{status:'LOCK',eps:null,verified:false,source:null,asOf:null,note:'Недостаточно проверенных данных для peer P/E.'},
 MGNT:{status:'LOCK',eps:null,verified:false,source:null,asOf:null,note:'Недостаточно проверенных данных для peer P/E.'},
 LENT:{status:'LOCK',eps:null,verified:false,source:null,asOf:null,note:'Недостаточно проверенных данных для peer P/E.'}
};
function get(t){return REGISTRY[t]||{status:'LOCK',eps:null,verified:false,source:null,asOf:null,note:'Peer EPS отсутствует в registry.'};}
function usable(t){const x=get(t);return x.verified===true&&Number.isFinite(Number(x.eps))&&Number(x.eps)>0&&!!x.source&&!!x.asOf;}
global.InvestorRadarPeerEarnings={REGISTRY,get,usable};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarPeerEarnings;
})(typeof window!=='undefined'?window:globalThis);
