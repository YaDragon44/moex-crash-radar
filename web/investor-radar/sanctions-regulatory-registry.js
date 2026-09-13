// Investor Radar R1.8.26 — Sanctions & Regulatory Registry Semantics Hardening
// DESIGNATED/MATERIAL sanctions risk is not thesis destruction and is never an automatic SELL trigger.
// Snapshot verified 2026-09-10 from primary sanctions authorities. Absence of designation is NOT inferred as clean status.
(function(global){
'use strict';
const AS_OF='2026-09-10';
const R={
 SBER:{verified:true,material:true,designated:true,level:'HIGH',status:'DESIGNATED',asOf:AS_OF,items:['ПАО Сбербанк находится под блокирующими санкциями OFAC (EO 14024).','UK Sanctions List: RUS0256; asset freeze и иные финансовые ограничения.'],sources:['US Treasury/OFAC 2022-04-06; OFAC update 2026-01-08','UK Sanctions List RUS0256']},
 MOEX:{verified:true,material:true,designated:true,level:'HIGH',status:'DESIGNATED',asOf:AS_OF,items:['ПАО Московская Биржа включено OFAC в SDN/Russia-related sanctions framework.','UK designation RUS2114; санкции введены 13.06.2024.'],sources:['OFAC Russia-related designation 2024-06-12; OFAC FAQ 1183','UK Sanctions List / FCDO RUS2114']},
 YDEX:{verified:false,material:false,designated:false,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['Нельзя переносить санкционный статус АО «Яндекс Банк» на МКПАО «Яндекс» без проверки юридического лица и правила владения/контроля.','UK 16.06.2026 обозначил именно JOINT STOCK COMPANY YANDEX BANK (RUS3621).'],sources:['UK Sanctions List RUS3621']},
 X5:{verified:false,material:false,designated:false,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['Недостаточно первичных данных для подтверждения полного sanctions/regulatory статуса МКПАО «Корпоративный центр ИКС 5».','Отсутствие найденного совпадения в поиске не считается доказательством отсутствия санкций.'],sources:[]}
};
function get(t){return R[String(t||'').toUpperCase()]||{verified:false,material:false,designated:false,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['Нет записи в sanctions/regulatory registry.'],sources:[]}}
function validate(x){
 const r=x||{};
 const errors=[];
 if(r.critical!==undefined) errors.push('legacy_critical_field_forbidden');
 if(r.verified===true&&typeof r.material!=='boolean') errors.push('material_boolean_required');
 if(r.verified===true&&typeof r.designated!=='boolean') errors.push('designated_boolean_required');
 if(r.designated===true&&r.material!==true) errors.push('designated_must_be_material');
 if(r.designated===true&&r.status!=='DESIGNATED') errors.push('designated_status_mismatch');
 return {ok:errors.length===0,errors};
}
function audit(){
 const errors=[];
 for(const [ticker,row] of Object.entries(R)){
  const v=validate(row); if(!v.ok) errors.push(...v.errors.map(e=>ticker+':'+e));
 }
 return {ok:errors.length===0,errors,rule:'sanctions material/designated semantics are separate from issuer thesisBroken and issuer critical risk'};
}
global.InvestorRadarSanctions={AS_OF,registry:R,get,validate,audit};
if(typeof module!=='undefined'&&module.exports)module.exports=global.InvestorRadarSanctions;
})(typeof window!=='undefined'?window:globalThis);
