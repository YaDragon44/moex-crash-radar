// Investor Radar R1.8.37 — Final SBER Equity Evidence Gate
// Purpose: close only the remaining bank-valuation evidence gap without using total-capital shortcuts.
(function(global){
'use strict';
const BASE=Object.freeze({
 ticker:'SBER',
 cbrCharterRevisionApproved:'2025-07-25',
 cbrCharterRegistered:'2025-07-28',
 cbrInstitutionSource:'Bank of Russia financial institution profile',
 cbrInstitutionSourceUrl:'https://cbr.ru/finorg/foinfo/?id=1315037838265',
 commonIssueSize:21586948000,
 preferredIssueSize:1000000000,
 nominalRub:3,
 commonSecuritySource:'MOEX SBER security profile',
 commonSecuritySourceUrl:'https://www.moex.com/ru/stocks/SBER',
 preferredSecuritySource:'MOEX SBERP security profile',
 preferredSecuritySourceUrl:'https://www.moex.com/ru/listing/securities-cards.aspx?code=20301481B',
 commonDividend2025Rub:37.64,
 preferredDividend2025Rub:37.64,
 dividendSource:'Sberbank 2026 annual shareholder meeting disclosure',
 dividendSourceUrl:'https://disclosure.1prime.ru/catalog/-12/%7B77DE79A4-CD30-4D34-984E-FC8D3312D48C%7D.uif',
 treasuryShareBasisVerified:true,
 treasuryCommonShares:0,
 commonSharesOutstanding:21586948000,
 treasurySource:'Bank of Russia form 0409810 as of 01.01.2026',
 treasurySourceUrl:'https://cbr.ru/banking_sector/credit/coinfo/f810/1904/?dt=202601&regnum=1481',
 statutoryCapitalRub:8115080880000,
 statutoryCapitalIsCommonEquity:false,
 moexTotalEquityCapitalRub:7942800000000,
 moexTotalEquityIsCommonEquity:false
});
function positive(x){return Number.isFinite(Number(x))&&Number(x)>0;}
function assess(extra={}){
 const missing=[];
 if(BASE.treasuryShareBasisVerified!==true||!positive(BASE.commonSharesOutstanding)) missing.push('treasury_outstanding_share_basis');
 if(extra.currentCharterRightsVerified!==true) missing.push('current_charter_preferred_rights');
 if(extra.preferredLiquidationRuleVerified!==true) missing.push('preferred_liquidation_priority');
 if(extra.equityAllocationMethodVerified!==true) missing.push('equity_allocation_method');
 if(extra.attributableCommonEquityVerified!==true||!positive(extra.attributableCommonEquityRub)) missing.push('attributable_common_equity');
 if(extra.primaryEquitySourceVerified!==true||!extra.primaryEquitySourceUrl) missing.push('primary_equity_source');
 const verified=missing.length===0;
 const commonEquity=verified?Number(extra.attributableCommonEquityRub):null;
 const bvps=verified?commonEquity/BASE.commonSharesOutstanding:null;
 return {
  status:verified?'VERIFIED':'PARTIAL',verified,missing,
  commonSharesOutstanding:BASE.commonSharesOutstanding,
  attributableCommonEquityRub:commonEquity,
  commonBvps:bvps,
  charterRevision:{approved:BASE.cbrCharterRevisionApproved,registered:BASE.cbrCharterRegistered,sourceUrl:BASE.cbrInstitutionSourceUrl},
  facts:{commonIssueSize:BASE.commonIssueSize,preferredIssueSize:BASE.preferredIssueSize,nominalRub:BASE.nominalRub,commonDividend2025Rub:BASE.commonDividend2025Rub,preferredDividend2025Rub:BASE.preferredDividend2025Rub,treasuryCommonShares:BASE.treasuryCommonShares},
  forbiddenShortcuts:[
   'Do not treat Bank of Russia statutory/regulatory capital as attributable common equity.',
   'Do not treat MOEX total Equity (Capital) as attributable common equity.',
   'Do not infer residual-equity allocation from equal current dividends alone.'
  ],
  message:verified?'SBER common-equity basis is fully primary-source verified.':'Недостаточно данных для обоснованного вывода: common BVPS/P-B остаётся заблокирован.',
  rule:'Common BVPS may be VERIFIED only after current preferred-share rights, liquidation/equity priority, allocation method and attributable common equity are independently primary-source verified.'
 };
}
global.InvestorRadarSberFinalEquityEvidence={BASE,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberFinalEquityEvidence;
})(typeof window!=='undefined'?window:globalThis);
