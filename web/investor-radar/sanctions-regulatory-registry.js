// Investor Radar R1.8.5 — Sanctions & Regulatory Registry
// Snapshot verified 2026-09-10 from primary sanctions authorities. Absence of a designation is NOT inferred as verified clean status.
(function(global){
'use strict';
const AS_OF='2026-09-10';
const R={
 SBER:{verified:true,critical:true,level:'HIGH',status:'DESIGNATED',asOf:AS_OF,items:['ПАО Сбербанк находится под блокирующими санкциями OFAC (EO 14024).','UK Sanctions List: RUS0256; asset freeze и иные финансовые ограничения.'],sources:['US Treasury/OFAC 2022-04-06; OFAC update 2026-01-08','UK Sanctions List RUS0256']},
 MOEX:{verified:true,critical:true,level:'HIGH',status:'DESIGNATED',asOf:AS_OF,items:['ПАО Московская Биржа включено OFAC в SDN/Russia-related sanctions framework.','UK designation RUS2114; санкции введены 13.06.2024.'],sources:['OFAC Russia-related designation 2024-06-12; OFAC FAQ 1183','UK Sanctions List / FCDO RUS2114']},
 YDEX:{verified:false,critical:false,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['Нельзя переносить санкционный статус АО «Яндекс Банк» на МКПАО «Яндекс» без проверки юридического лица и правила владения/контроля.','UK 16.06.2026 обозначил именно JOINT STOCK COMPANY YANDEX BANK (RUS3621).'],sources:['UK Sanctions List RUS3621']},
 X5:{verified:false,critical:false,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['Недостаточно первичных данных для подтверждения полного sanctions/regulatory статуса МКПАО «Корпоративный центр ИКС 5».','Отсутствие найденного совпадения в поиске не считается доказательством отсутствия санкций.'],sources:[]}
};
function get(t){return R[t]||{verified:false,critical:false,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['Нет записи в sanctions/regulatory registry.'],sources:[]}}
global.InvestorRadarSanctions={AS_OF,registry:R,get};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSanctions;
})(typeof window!=='undefined'?window:globalThis);
