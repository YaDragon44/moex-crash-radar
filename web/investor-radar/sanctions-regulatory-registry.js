// Investor Radar R1.8.26 — Sanctions & Regulatory Registry Semantics Hardening
// DESIGNATED/MATERIAL sanctions risk is not thesis destruction and is never an automatic SELL trigger.
// Snapshot verified 2026-09-10 from primary sanctions authorities. Absence of designation is NOT inferred as clean status.
(function(global){
'use strict';
const AS_OF='2026-09-24';
const R={
 SBER:{verified:true,material:true,designated:true,level:'HIGH',status:'DESIGNATED',asOf:AS_OF,items:['ПАО Сбербанк находится под блокирующими санкциями OFAC (EO 14024).','UK Sanctions List: RUS0256; asset freeze и иные финансовые ограничения.'],sources:['US Treasury/OFAC 2022-04-06; OFAC update 2026-01-08','UK Sanctions List RUS0256']},
 MOEX:{verified:true,material:true,designated:true,level:'HIGH',status:'DESIGNATED',asOf:AS_OF,items:['ПАО Московская Биржа включено OFAC в SDN/Russia-related sanctions framework.','UK designation RUS2114; санкции введены 13.06.2024.'],sources:['OFAC Russia-related designation 2024-06-12; OFAC FAQ 1183','UK Sanctions List / FCDO RUS2114']},
 YDEX:{verified:true,material:true,designated:false,level:'HIGH',status:'SUBSIDIARY_RESTRICTED',asOf:AS_OF,items:['МКПАО «Яндекс» не приравнивается к АО «Яндекс Банк»: санкционный статус дочернего банка не переносится вверх на головную компанию.','EU Decision (CFSP) 2025/1495 added Yandex Bank to the transaction-ban list; UK Sanctions List separately designates JOINT STOCK COMPANY "YANDEX BANK" as RUS3621 from 16.06.2026.','Issuer disclosure states the EU restrictions on Yandex Bank do not extend to head company MKPAO Yandex or other group subsidiaries. This is treated as material group sanctions exposure, not designation of YDEX itself.'],sources:['EU Council Decision (CFSP) 2025/1495 / EUR-Lex','UK Sanctions List RUS3621 / FCDO','Yandex issuer disclosure 2025-07-19']},
 X5:{verified:false,material:null,designated:null,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['EU sanctions materials concerning sanctioned Alfa Group shareholders mention historical X5 Retail Group in their statements of reasons, but that is not an entity designation of current PJSC X5 Corporate Center.','Current PJSC X5 Corporate Center has a post-redomiciliation shareholder structure; available primary evidence in this review is insufficient to prove current ownership/control attribution under sanctions rules.','Absence of a direct-list search match is not proof of sanctions-free status; X5 therefore remains LOCK/UNKNOWN.'],sources:['EU Council restrictive-measures materials concerning Alfa Group shareholders','X5 share distribution / current shares disclosures']},
 GAZP:{verified:true,material:true,designated:false,level:'HIGH',status:'SECTORAL_RESTRICTIONS',asOf:'2026-09-23',items:['PUBLIC JOINT STOCK COMPANY GAZPROM is explicitly listed by OFAC on a Non-SDN sanctions list.','PJSC Gazprom is subject to EO 14024 Directive 3 restrictions on new debt over 14 days and new equity issued on/after the effective date, and is also subject to EO 13662 Directive 4.','This is material entity-specific sanctions evidence, but it is not an SDN/blocking designation; Gazprom Neft and Gazprombank statuses are not substituted for PJSC Gazprom.','Material sectoral/directive restrictions do not automatically imply issuer thesisBroken or SELL.'],sources:['US Treasury/OFAC Russia-related action 2022-02-24','OFAC Sanctions List Search: PUBLIC JOINT STOCK COMPANY GAZPROM, Non-SDN']},
 AFLT:{verified:true,material:true,designated:true,level:'HIGH',status:'DESIGNATED',asOf:'2026-09-21',items:['PJSC AEROFLOT is designated on the UK Sanctions List as RUS1444; listed 19 May 2022.','UK entry applies an asset freeze and trust-services sanctions; this is entity-specific evidence, not merely sectoral aviation restrictions.','Designation/material sanctions risk does not automatically imply issuer thesisBroken or SELL.'],sources:['UK Sanctions List RUS1444 / FCDO, current list 2026-09-21']},
 VKCO:{verified:true,material:true,designated:true,level:'HIGH',status:'DESIGNATED',asOf:'2026-07-13',items:['МКПАО «ВК» раскрыла применение ограничительных мер Европейского Союза в июле 2026 года.','Компания заявила, что не ожидает существенного влияния мер на операционную деятельность; это позиция эмитента, а не вывод risk model.','Designation/material sanctions risk не означает автоматически thesisBroken или SELL.'],sources:['VK H1 2026 results, 2026-08-13','EU restrictive measures disclosed by issuer, July 2026']}
};
function get(t){return R[String(t||'').toUpperCase()]||{verified:false,material:null,designated:null,level:'UNKNOWN',status:'LOCK',asOf:AS_OF,items:['Нет записи в sanctions/regulatory registry.'],sources:[]}}
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
