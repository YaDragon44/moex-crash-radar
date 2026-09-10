// Investor Radar R1.8.13 — Exact EPS Extraction
// VERIFIED peer EPS requires an exact comparable per-share earnings metric from a primary source.
// A verified negative EPS is valid evidence but is NOT usable for P/E.
(function(global){
'use strict';
const REGISTRY={
 VTBR:{status:'PARTIAL',eps:null,verified:false,metric:null,comparable:false,source:'VTB Group IFRS Financial Results',sourceUrl:'https://www.vtb.com/ir/financial-results/ifrs-financial-results',asOf:'2025-12-31',evidence:['Issuer publishes VTB Group FY2025 IFRS results; exact comparable EPS has not yet been extracted.'],note:'Primary source exists, but exact comparable EPS is still missing. Peer P/E remains LOCK.'},
 T:{status:'PARTIAL',eps:null,verified:false,metric:'OPERATING_NET_PROFIT_PER_SHARE_PRO_FORMA_PRE_SPLIT',comparable:false,reportedValue:650,unit:'RUB/share pre 1:10 split',source:'T-Technologies Annual Report 2025',sourceUrl:'https://t-technologies.ru/ar2025t-technologies/index.html',asOf:'2025-12-31',evidence:['Issuer reports RUB 650 operating net profit per share on a pre-split pro-forma basis.','April 2026 stock split was 1:10.'],note:'This is not an explicitly verified IFRS basic/diluted EPS. Do not substitute it into P/E.'},
 VKCO:{status:'LOCK',eps:null,verified:false,metric:null,comparable:false,source:null,sourceUrl:null,asOf:null,evidence:[],note:'Exact comparable EPS from a primary source not verified.'},
 OZON:{status:'LOCK',eps:null,verified:false,metric:null,comparable:false,source:null,sourceUrl:null,asOf:null,evidence:[],note:'Exact comparable EPS from a primary source not verified.'},
 MGNT:{status:'VERIFIED_EXCLUDED',eps:-455.28,verified:true,metric:'IFRS_BASIC_LOSS_PER_SHARE',comparable:true,source:'PJSC Magnit FY2025 IFRS Audited Financial Statements, Note 31',sourceUrl:'https://www.magnit.com/upload/iblock/6d7/479nkl2oc0ozalg4krkm0saadlrfdrmf/FY%202025%20IFRS%20Audited%20Financial%20Statements.pdf',asOf:'2025-12-31',evidence:['Loss attributable to shareholders: RUB 30,889.711 million.','Weighted average shares: 67.847 million.','Basic loss per share: RUB -455.28; diluted loss per share: RUB -455.28.'],note:'Exact IFRS EPS is verified, but it is negative. MGNT is automatically excluded from peer P/E.'},
 LENT:{status:'PARTIAL',eps:null,verified:false,metric:'NET_PROFIT_ONLY',comparable:false,source:'Lenta Group Q4/FY2025 Financial Results',sourceUrl:'https://www.lentagroup.ru/upload/iblock/79f/a33uclr7trw3p2nigq6f5pjkklua1poe/Lenta_Group_Q425_Financial_Results_ENG_vF.pdf',asOf:'2025-12-31',evidence:['FY2025 net profit is disclosed, but exact IFRS EPS/share denominator was not verified.'],note:'Net profit alone cannot unlock peer P/E.'}
};
function get(t){return REGISTRY[t]||{status:'LOCK',eps:null,verified:false,metric:null,comparable:false,source:null,sourceUrl:null,asOf:null,evidence:[],note:'Peer EPS отсутствует в registry.'};}
function usable(t){const x=get(t);return x.verified===true&&x.comparable===true&&Number.isFinite(Number(x.eps))&&Number(x.eps)>0&&!!x.source&&!!x.asOf;}
function audit(t){const x=get(t),missing=[];if(x.verified!==true)missing.push('verified_eps');if(x.comparable!==true)missing.push('comparable_metric');if(!(Number.isFinite(Number(x.eps))&&Number(x.eps)>0))missing.push(Number.isFinite(Number(x.eps))?'positive_eps':'eps');if(!x.source||!x.asOf)missing.push('source_metadata');return {ticker:t,status:x.status,usable:usable(t),missing,note:x.note};}
global.InvestorRadarPeerEarnings={REGISTRY,get,usable,audit};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarPeerEarnings;
})(typeof window!=='undefined'?window:globalThis);
