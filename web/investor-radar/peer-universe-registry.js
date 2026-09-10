// Investor Radar R1.8.10 — Peer Universe Registry
// Peer membership is a methodology decision, not a valuation fact. P/E values remain empty until verified by Data Factory.
(function(global){
'use strict';
const REGISTRY={
 SBER:{sector:'BANKS',status:'APPROVED_UNIVERSE',peers:['VTBR','T'],metric:'P/E',note:'Российские публичные банки/финансовые группы. Не смешивать с non-financial issuers.'},
 YDEX:{sector:'INTERNET_TECH',status:'APPROVED_UNIVERSE',peers:['VKCO','OZON'],metric:'P/E',note:'Российские публичные internet/tech/platform peers. P/E применим только при положительной сопоставимой прибыли.'},
 X5:{sector:'FOOD_RETAIL',status:'APPROVED_UNIVERSE',peers:['MGNT','LENT'],metric:'P/E',note:'Российский food retail. Проверять сопоставимость IFRS16 и структуры прибыли.'},
 MOEX:{sector:'EXCHANGE_INFRASTRUCTURE',status:'LIMITED_UNIVERSE',peers:[],metric:'P/E',note:'На MOEX нет двух очевидных прямых российских публичных аналогов. Нельзя искусственно подмешивать банки; peer gate остаётся LOCK до утверждения сопоставимого внешнего universe.'}
};
function get(t){return REGISTRY[t]||{sector:'UNKNOWN',status:'LOCK',peers:[],metric:null,note:'Peer universe не определён.'};}
function validate(t){const x=get(t);const unique=[...new Set(x.peers||[])];return {ticker:t,sector:x.sector,status:x.status,peers:unique,eligible:x.status==='APPROVED_UNIVERSE'&&unique.length>=2,metric:x.metric,note:x.note};}
global.InvestorRadarPeerUniverse={REGISTRY,get,validate};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarPeerUniverse;
})(typeof window!=='undefined'?window:globalThis);
