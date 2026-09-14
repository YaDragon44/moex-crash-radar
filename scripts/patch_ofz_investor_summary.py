from pathlib import Path

p=Path('web/ofz-radar/index.html')
s=p.read_text(encoding='utf-8')

# Idempotent release label.
s=s.replace('OFZ Signal Radar R0.5.3','OFZ Signal Radar R0.5.10')
s=s.replace('R0.5.3 Live Strategy Simulator','R0.5.10 Dashboard Investor Summary')

STYLE='''\n.investor-summary{margin-top:14px}.investor-grid{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:14px}.investor-title{font-size:24px;font-weight:850;margin:5px 0 10px}.investor-action{font-size:30px;font-weight:900;margin:7px 0}.investor-summary p{margin:7px 0}.riskline{padding-top:8px;margin-top:8px;border-top:1px solid #20344e}@media(max-width:1100px){.investor-grid{grid-template-columns:1fr}}\n'''
if '.investor-summary{' not in s:
    s=s.replace('</style>',STYLE+'</style>')

BLOCK='''\n<div id="investorSummary" class="investor-summary card"><div class="mut">Для долгосрочного инвестора · 5+ лет</div><div class="investor-grid"><section><div class="investor-title">Рынок сейчас</div><div id="marketNow"></div></section><section><div class="investor-title">Вывод</div><div id="investorConclusion"></div></section><section><div class="investor-title">Рекомендация</div><div id="investorRecommendation"></div></section></div></div>\n'''
if 'id="investorSummary"' not in s:
    s=s.replace('<script>',BLOCK+'<script>',1)

JS=r'''
function renderInvestorSummary(d){
 const pts=d.curve?.points||[], ten=pts.find(p=>p.years===10)?.yield, kr=Number(d.keyRate?.value), reg=d.rawRegime||'—', cr=d.confirmedRegime||{}, bonds=d.bonds||[];
 const valid=bonds.filter(b=>Number.isFinite(Number(b.ytm))&&Number.isFinite(Number(b.duration)));
 const best=[...valid].sort((a,b)=>Number(b.ytm)-Number(a.ytm))[0];
 let tone='НЕЙТРАЛЬНО', cls='y', market='Данных недостаточно для уверенной оценки.', conclusion='Сохраняем осторожность до восстановления полного набора официальных данных.', action='НАБЛЮДАТЬ', rec='Не увеличивать процентный риск без подтверждённой доходности и качества данных.';
 if(Number.isFinite(ten)){
   if(ten>=16){tone='ПРИВЛЕКАТЕЛЬНО';cls='g';market=`10Y ОФЗ ${fmt(ten)}% — высокая доходность длинного конца кривой. Ключевая ставка ${fmt(kr)}%. Режим ${reg}.`;conclusion='Для горизонта 5+ лет длинные фиксированные ОФЗ дают привлекательную стартовую доходность и высокий потенциал переоценки при будущем снижении ставок. Главный риск — высокая ставка и инфляция дольше ожиданий.';action=cr.blocked?'ПОКУПАТЬ ПОСТЕПЕННО':'ДОКУПАТЬ';rec='Набирать позицию частями, сохраняя запас для докупки при росте доходностей. Не продавать длинные ОФЗ только из-за краткосрочной волатильности.';}
   else if(ten>=14){tone='УМЕРЕННО ПРИВЛЕКАТЕЛЬНО';cls='g';market=`10Y ОФЗ ${fmt(ten)}%. Режим ${reg}: доходность всё ещё интересна, но часть премии уже могла быть реализована в цене.`;conclusion='Долгосрочная позиция оправдана, но соотношение доходности и процентного риска хуже, чем при 10Y выше 16%.';action='ДЕРЖАТЬ / ДОКУПАТЬ';rec='Основную позицию держать, новые покупки распределять во времени и контролировать инфляцию, КС и форму кривой.';}
   else if(ten>=12){tone='НЕЙТРАЛЬНО';cls='y';market=`10Y ОФЗ ${fmt(ten)}%. Режим ${reg}: значительная часть эффекта снижения ставок уже отражена в длинных бумагах.`;conclusion='Доходность остаётся положительной, но премия за длинную дюрацию сокращается.';action='ДЕРЖАТЬ';rec='Не наращивать длинную дюрацию агрессивно. Купоны реинвестировать выборочно.';}
   else if(ten>=10){tone='ОСТОРОЖНО';cls='y';market=`10Y ОФЗ ${fmt(ten)}%. Режим ${reg}: доходность длинных ОФЗ заметно снизилась.`;conclusion='Потенциал дальнейшей переоценки уменьшается, а чувствительность к обратному росту доходностей остаётся высокой.';action='ДЕРЖАТЬ / СОКРАЩАТЬ';rec='Частично фиксировать переоценку и постепенно уменьшать концентрацию в длинной дюрации.';}
   else {tone='ФИКСАЦИЯ ПРИБЫЛИ';cls='o';market=`10Y ОФЗ ${fmt(ten)}%. Режим ${reg}: длинные доходности находятся ниже 10%.`;conclusion='Компенсация за процентный риск стала низкой относительно длинной дюрации.';action='СОКРАЩАТЬ / РОТИРОВАТЬ';rec='Фиксировать часть прибыли и переводить капитал в более короткие инструменты/флоатеры после отдельной проверки их доходности.';}
 }
 $('marketNow').innerHTML=`<div class="investor-action ${cls}">${tone}</div><p>${market}</p><div class="riskline note">Raw regime <b>${reg}</b> · Confirmed <b>${cr.id||'—'}</b> · Confidence <b>${cr.confidence||'—'}</b>${cr.blocked?' · сигнал не подтверждён макрофакторами':''}</div>`;
 $('investorConclusion').innerHTML=`<p>${conclusion}</p><div class="riskline note">Риск: рост инфляции/доходностей способен вызвать заметную просадку длинных ОФЗ до погашения.</div>`;
 $('investorRecommendation').innerHTML=`<div class="investor-action ${cls}">${action}</div><p>${rec}</p>${best?`<div class="riskline note">Среди отслеживаемых выпусков максимальная текущая YTM: <b>ОФЗ ${best.secid}</b> ≈ <b>${fmt(best.ytm)}%</b>. Выбор выпуска нельзя делать только по YTM — учитываем duration, ликвидность и cashflow.</div>`:''}`;
}
'''
if 'function renderInvestorSummary(d)' not in s:
    # Insert helper immediately before the main render function.
    s=s.replace('function render(d){',JS+'\nfunction render(d){',1)
    # Invoke it at the beginning of main render.
    s=s.replace("function render(d){const c=d.curve", "function render(d){renderInvestorSummary(d);const c=d.curve",1)

p.write_text(s,encoding='utf-8')
print('R0.5.10 patch applied')
