// Investor Radar R1.8.12 — Peer Earnings Verification
// VERIFIED peer EPS requires an exact comparable per-share earnings metric from a primary source.
// Source existence, net profit alone, or adjusted/operating profit per share does NOT unlock P/E.
(function(global){
'use strict';
const REGISTRY={
 VTBR:{status:'PARTIAL',eps:null,verified:false,metric:null,comparable:false,source:'VTB Group IFRS Financial Results',sourceUrl:'https://www.vtb.com/ir/financial-results/ifrs-financial-results',asOf:'2025-12-31',evidence:['VTB Group FY2025 IFRS results published by issuer.'],note:'Primary source located, but exact comparable EPS was not extracted in this verification pass. Peer P/E remains LOCK.'},
 T:{status:'PARTIAL',eps:null,verified:false,metric:'OPERATING_NET_PROFIT_PER_SHARE_PRO_FORMA_PRE_SPLIT',comparable:false,reportedValue:650,unit:'RUB/share pre 1:10 split',source:'T-Technologies Annual Report 2025',sourceUrl:'https://t-technologies.ru/ar2025t-technologies/index.html',asOf:'2025-12-31',evidence:['Issuer reports 650 RUB operating net profit per share on a pre-split pro-forma basis.','April 2026 stock split was 1:10.'],note:'Metric is operating/adjusted profit per share, not an explicitly verified IFRS basic/diluted EPS for peer P/E. Do not substitute it.'},
 VKCO:{status:'LOCK',eps:null,verified:false,metric:null,comparable:false,source:null,sourceUrl:null,asOf:null,evidence:[],note:'Exact positive comparable EPS from a primary source not verified. P/E remains unusable.'},
 OZON:{status:'LOCK',eps:null,verified:false,metric:null,comparable:false,source:null,sourceUrl:null,asOf:null,evidence:[],note:'Exact comparable EPS from a primary source not verified in this pass.'},
 MGNT:{status:'LOCK',eps:null,verified:false,metric:null,comparable:false,source:null,sourceUrl:null,asOf:null,evidence:[],note:'Exact comparable EPS from a primary source not verified in this pass.'},
 LENT:{status:'PARTIAL',eps:null,verified:false,metric:'NET_PROFIT_ONLY',comparable:false,source:'Lenta Group Q4/FY2025 Financial Results',sourceUrl:'https://www.lentagroup.ru/upload/iblock/79f/a33uclr7trw3p2nigq6f5pjkklua1poe/Lenta_Group_Q425_Financial_Results_ENG_vF.pdf',asOf:'2025-12-31',evidence:['Issuer FY2025 results report net profit of RUB 38,234 million pre-IFRS 16.'],note:'Net profit is verified, but exact comparable EPS/share denominator was not verified; peer P/E remains LOCK.'}
};
function get(t){return REGISTRY[t]||{status:'LOCK',eps:null,verified:false,metric:null,comparable:false,source:null,sourceUrl:null,asOf:null,evidence:[],note:'Peer EPS отсутствует в registry.'};}
function usable(t){const x=get(t);return x.verified===true&&x.comparable===true&&Number.isFinite(Number(x.eps))&&Number(x.eps)>0&&!!x.source&&!!x.asOf;}
function audit(t){const x=get(t);const missing=[];if(x.verified!==true)missing.push('verified_eps');if(x.comparable!==true)missing.push('comparable_metric');if(!(Number.isFinite(Number(x.eps))&&Number(x.eps)>0))missing.push('positive_eps');if(!x.source||!x.asOf)missing.push('source_metadata');return {ticker:t,status:x.status,usable:usable(t),missing,note:x.note};}
global.InvestorRadarPeerEarnings={REGISTRY,get,usable,audit};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarPeerEarnings;
})(typeof window!=='undefined'?window:globalThis);
