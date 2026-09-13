// Investor Radar R1.8.35 — SBER Preferred-Share Treatment Evidence
// Facts about SBERP are recorded separately from the valuation conclusion.
// Equal dividends do NOT prove that total shareholder equity may be allocated pro-rata for common BVPS.
(function(global){
'use strict';
const EVIDENCE=Object.freeze({
 ticker:'SBER',
 preferredTicker:'SBERP',
 preferredIsin:'RU0009029557',
 preferredIssueSize:1000000000,
 preferredFaceValueRub:3,
 commonDividend2025Rub:37.64,
 preferredDividend2025Rub:37.64,
 dividendSource:'Interfax Corporate Disclosure Center — Sberbank board recommendation / 2025 profit distribution',
 dividendSourceUrl:'https://www.e-disclosure.ru/portal/event.aspx?EventId=7tSumUE9bUa3nmDlDRhZaQ-B-B',
 securitySource:'MOEX SBERP security profile',
 securitySourceUrl:'https://www.moex.com/en/issue.aspx?code=SBERP',
 asOf:'2026-09-11',
 currentCharterLiquidationRightsVerified:false,
 currentCharterEquityPriorityVerified:false,
 equityAllocationMethodVerified:false
});

function assess(){
 const dividendEquality=Number(EVIDENCE.commonDividend2025Rub)===Number(EVIDENCE.preferredDividend2025Rub);
 const securityOk=EVIDENCE.preferredIssueSize>0&&EVIDENCE.preferredFaceValueRub>0&&!!EVIDENCE.preferredIsin&&!!EVIDENCE.securitySourceUrl;
 const distributionOk=dividendEquality&&!!EVIDENCE.dividendSourceUrl;
 const preferredTreatmentVerified=EVIDENCE.currentCharterLiquidationRightsVerified===true&&EVIDENCE.currentCharterEquityPriorityVerified===true&&EVIDENCE.equityAllocationMethodVerified===true;
 const missing=[];
 if(!securityOk) missing.push('preferred_security_terms');
 if(!distributionOk) missing.push('current_dividend_treatment');
 if(!EVIDENCE.currentCharterLiquidationRightsVerified) missing.push('current_charter_liquidation_rights');
 if(!EVIDENCE.currentCharterEquityPriorityVerified) missing.push('current_charter_equity_priority');
 if(!EVIDENCE.equityAllocationMethodVerified) missing.push('equity_allocation_method');
 return {
  status:preferredTreatmentVerified?'VERIFIED':'PARTIAL',
  verified:preferredTreatmentVerified,
  preferredTreatmentVerified,
  dividendEqualityVerified:distributionOk,
  preferredSecurityVerified:securityOk,
  missing,
  facts:[
   'SBERP is a separate preferred share class, ISIN RU0009029557, issue size 1,000,000,000, face value 3 RUB.',
   'For 2025 Sberbank recommended/approved equal dividends of 37.64 RUB per common and preferred share.'
  ],
  interpretation:'Equal current dividends demonstrate distribution parity for the period, but do not establish liquidation priority or a defensible allocation of total equity between common and preferred shares.',
  conclusion:preferredTreatmentVerified?'Preferred-share treatment is sufficient for common-BVPS allocation.':'Недостаточно данных для обоснованного вывода о распределении капитала между SBER и SBERP.',
  rule:'Do not allocate total equity pro-rata across common/preferred shares until current charter/issue rights and the allocation method are primary-source verified.'
 };
}

global.InvestorRadarSberPreferredTreatment={EVIDENCE,assess};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSberPreferredTreatment;
})(typeof window!=='undefined'?window:globalThis);
