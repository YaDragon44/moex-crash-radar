// Investor Radar R1.8.38 — SBER Current Charter Rights Acquisition Gate
// Separates historical preferred-share rights from the current 2025 charter revision.
// Historical rights are evidence, not a substitute for current-charter verification.
(function(global){
'use strict';
const EVIDENCE=Object.freeze({
 ticker:'SBER',
 currentCharter:{
  approved:'2025-07-25',registered:'2025-07-28',
  source:'Bank of Russia financial institution profile',
  sourceUrl:'https://cbr.ru/finorg/foinfo/?id=1315037838265',
  textRetrieved:false,
  preferredRightsTextVerified:false
 },
 historicalPreferredRights:{
  sourceDate:'2014',
  source:'Interfax Corporate Disclosure Center — historical Sberbank charter rights disclosure',
  sourceUrl:'https://www.e-disclosure.ru/portal/event.aspx?EventId=J19RYikTu0qDVH6QuQMvBA-B-B',
  dividendParityWithCommon:true,
  liquidationValueRub:1000,
  votingNormally:false,
  historicalOnly:true
 },
 currentSecurityIdentity:{
  preferredTicker:'SBERP',isin:'RU0009029557',issueRegistration:'20301481B',
  source:'MOEX current SBERP security profile',
  sourceUrl:'https://www.moex.com/ru/listing/securities-cards.aspx?code=20301481B'
 },
 currentDividendParity:{
  year:2025,commonDividendRub:37.64,preferredDividendRub:37.64,
  source:'Sberbank 2026 annual shareholder meeting disclosure',
  sourceUrl:'https://www.e-disclosure.ru/portal/event.aspx?EventId=7tSumUE9bUa3nmDlDRhZaQ-B-B'
 }
});

function assess(extra={}){
 const currentTextVerified=extra.currentCharterTextVerified===true&&!!extra.currentCharterTextSourceUrl;
 const liquidationVerified=currentTextVerified&&extra.currentLiquidationValueVerified===true&&Number.isFinite(Number(extra.currentLiquidationValueRub));
 const dividendRightsVerified=currentTextVerified&&extra.currentDividendRightsVerified===true;
 const votingRightsVerified=currentTextVerified&&extra.currentVotingRightsVerified===true;
 const equityPriorityVerified=currentTextVerified&&extra.currentEquityPriorityVerified===true;
 const missing=[];
 if(!currentTextVerified) missing.push('current_charter_text');
 if(!liquidationVerified) missing.push('current_liquidation_right');
 if(!dividendRightsVerified) missing.push('current_dividend_right');
 if(!votingRightsVerified) missing.push('current_voting_right');
 if(!equityPriorityVerified) missing.push('current_equity_priority');
 const verified=missing.length===0;
 return {
  status:verified?'VERIFIED':'PARTIAL',verified,missing,
  currentCharterRevision:EVIDENCE.currentCharter,
  historicalRights:EVIDENCE.historicalPreferredRights,
  currentSecurityIdentity:EVIDENCE.currentSecurityIdentity,
  currentDividendParity:EVIDENCE.currentDividendParity,
  currentRights:verified?{
   liquidationValueRub:Number(extra.currentLiquidationValueRub),
   dividendRightsVerified:true,votingRightsVerified:true,equityPriorityVerified:true,
   sourceUrl:extra.currentCharterTextSourceUrl
  }:null,
  interpretation:verified?'Current preferred-share rights are primary-source verified against the latest charter text.':'Latest charter revision metadata is current, but the exact 2025 charter text governing SBERP rights has not been retrieved and verified. Historical 2014 rights and 2025 dividend parity cannot be silently carried forward.',
  message:verified?'Current SBERP charter rights verified.':'Недостаточно данных для обоснованного вывода о текущем приоритете SBERP в капитале/ликвидации.',
  rule:'Historical preferred-share rights may be used only as a search baseline. They cannot unlock common-equity allocation until the current charter text is independently verified.'
 };
}

global.InvestorRadarSberCurrentCharterRights={EVIDENCE,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberCurrentCharterRights;
})(typeof window!=='undefined'?window:globalThis);
