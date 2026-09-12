// TA Market R0.9.2 production safety + execution risk + observation patch.
// snapshot age ≤25m safety gate: implemented via age <= 25, snapshotFresh and STALE snapshot fallback.
(function(){
  const originalAnalyze = window.analyze;
  if (typeof originalAnalyze === 'function') {
    window.analyze = function(id){
      const a = originalAnalyze(id);
      if (!a || !a.plan) return a;
      const t = Date.parse(J?.generated_at || '');
      const age = Number.isFinite(t) ? (Date.now() - t) / 60000 : Infinity;
      const snapshotFresh = age >= 0 && age <= 25;
      a.plan.checks = {...(a.plan.checks || {}), snapshot:snapshotFresh};
      if (!snapshotFresh && a.plan.status === 'READY') {
        a.plan.status = 'WAIT';
        a.plan.reason = 'STALE snapshot';
      }
      return a;
    };
    analyze = window.analyze;
  }

  window.score = function(a){
    if (!a || a.plan?.dir === 'NEUTRAL') return 0;
    let s = 0;
    if ((a.plan.dir === 'LONG' && a.st?.label === 'HH / HL') ||
        (a.plan.dir === 'SHORT' && a.st?.label === 'LH / LL')) s += 2;
    if (Number.isFinite(+a.plan?.entry) && Number.isFinite(+a.plan?.stop)) s += 2;
    if (a.plan?.checks?.rvol) s += 2;
    if (a.fi) s += 1;
    if (a.pr) s += 1;
    if (a.plan?.checks?.momentum) s += 1;
    const rr = +a.plan?.rr;
    if (Number.isFinite(rr)) s += rr >= 3 ? 3 : rr >= 2 ? 2 : rr >= 1 ? 1 : 0;
    if (a.plan?.checks?.market) s += 2;
    return Math.min(19, s);
  };
  score = window.score;

  const LS='ta_market_risk_v085';
  const loadCfg=()=>{try{return {...{capital:0,riskPct:0,commissionPct:0,slippagePct:0},...JSON.parse(localStorage.getItem(LS)||'{}')}}catch(e){return{capital:0,riskPct:0,commissionPct:0,slippagePct:0}}};
  const saveCfg=c=>localStorage.setItem(LS,JSON.stringify(c));
  const money=x=>Number.isFinite(+x)?(+x).toLocaleString('ru-RU',{maximumFractionDigits:0})+' ₽':'N/A';
  const num=(x,d=2)=>Number.isFinite(+x)?(+x).toLocaleString('ru-RU',{minimumFractionDigits:d,maximumFractionDigits:d}):'N/A';
  const pct=x=>Number.isFinite(+x)?num(+x,1)+'%':'N/A';
  const rval=x=>Number.isFinite(+x)?num(+x,2)+'R':'N/A';
  let PERF=null;

  function riskCalc(a){
    const c=loadCfg(), md=J?.securities?.[sel]?.marketdata||{};
    const lot=Math.max(1,Math.floor(+md.LOTSIZE||1));
    const entry=+a?.plan?.entry, stop=+a?.plan?.stop;
    if(!(c.capital>0&&c.riskPct>0&&Number.isFinite(entry)&&Number.isFinite(stop)&&entry>0)) return {lot,valid:false};
    const allowed=c.capital*c.riskPct/100;
    const stopRisk=Math.abs(entry-stop);
    const friction=entry*(2*c.commissionPct+2*c.slippagePct)/100;
    const perShare=stopRisk+friction;
    const perLot=perShare*lot;
    let lots=perLot>0?Math.floor(allowed/perLot):0;
    const maxLots=Math.floor(c.capital/(entry*lot));
    lots=Math.max(0,Math.min(lots,maxLots));
    const shares=lots*lot;
    return {lot,valid:true,allowed,stopRisk,friction,perShare,perLot,lots,shares,position:shares*entry,moneyRisk:lots*perLot};
  }

  function ensureRiskBox(){
    if(document.getElementById('riskbox')) return;
    const aside=document.querySelector('aside.panel'); if(!aside) return;
    const box=document.createElement('div'); box.id='riskbox';
    box.innerHTML='<div class="section">Риск и размер позиции</div><div class="trade" id="riskinputs"></div><div class="trade" id="riskout"></div><div class="gate" id="risknote">Введите капитал и риск % — без них размер позиции не рассчитывается.</div>';
    aside.appendChild(box);
  }

  function drawRisk(){
    ensureRiskBox(); if(!window.J||!window.sel) return;
    const c=loadCfg(), a=window.analyze?.(sel), r=riskCalc(a);
    const inp=document.getElementById('riskinputs'), out=document.getElementById('riskout'); if(!inp||!out)return;
    const field=(k,label,step)=>`<label class="kv"><div class="k">${label}</div><input data-risk="${k}" type="number" min="0" step="${step}" value="${c[k]||0}" style="width:100%;margin-top:5px;background:#0a1119;color:var(--tx);border:1px solid var(--ln);border-radius:6px;padding:6px"></label>`;
    inp.innerHTML=field('capital','Капитал ₽','1000')+field('riskPct','Риск %','0.1')+field('commissionPct','Комиссия % / сторона','0.001')+field('slippagePct','Проскальзывание % / сторона','0.001');
    inp.querySelectorAll('[data-risk]').forEach(el=>el.onchange=()=>{c[el.dataset.risk]=Math.max(0,+el.value||0);saveCfg(c);drawRisk()});
    out.innerHTML=[['Лот MOEX',r.lot],['Допустимый риск',r.valid?money(r.allowed):'N/A'],['Риск/акция',r.valid?num(r.perShare,2)+' ₽':'N/A'],['Риск/лот',r.valid?money(r.perLot):'N/A'],['Лотов',r.valid?r.lots:'N/A'],['Акций',r.valid?r.shares:'N/A'],['Размер позиции',r.valid?money(r.position):'N/A'],['Денежный риск',r.valid?money(r.moneyRisk):'N/A']].map(([k,v])=>`<div class="kv"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
    document.getElementById('risknote').textContent=r.valid?(r.lots>0?'Без плеча · комиссия и проскальзывание учтены на входе и выходе.':'При заданном риске корректный стоп/издержки не позволяют открыть даже 1 лот.'):'Введите капитал и риск % — без них размер позиции не рассчитывается.';
  }

  function ensurePerfBox(){
    if(document.getElementById('perfbox')) return;
    const aside=document.querySelector('aside.panel'); if(!aside) return;
    const box=document.createElement('div'); box.id='perfbox';
    box.innerHTML='<div class="section">Production Observation</div><div class="trade" id="perfsummary"></div><div class="gate" id="samplequality">Sample Quality: N/A</div><div class="gate" id="perfnote">Загрузка статистики модели…</div><div id="perfdetail" style="font-size:11px;line-height:1.5;margin-top:8px"></div>';
    aside.appendChild(box);
  }

  function compactStats(obj){
    if(!obj) return 'нет данных';
    const closed=+obj.closed||0, signals=+obj.signals||0;
    return `${signals} сигналов · ${closed} закрыто · WR ${pct(obj.win_rate)} · Exp ${rval(obj.expectancy_r)}`;
  }

  function drawPerf(){
    ensurePerfBox();
    const sum=document.getElementById('perfsummary'), quality=document.getElementById('samplequality'), note=document.getElementById('perfnote'), detail=document.getElementById('perfdetail');
    if(!sum||!quality||!note||!detail)return;
    if(!PERF){
      sum.innerHTML=[['READY signals','N/A'],['Closed','N/A'],['Win Rate','N/A'],['Expectancy','N/A'],['Profit Factor','N/A']].map(([k,v])=>`<div class="kv"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
      quality.textContent='Sample Quality: N/A';
      note.textContent='Статистика модели недоступна; торговые сигналы продолжают работать.';
      detail.innerHTML=''; return;
    }
    const s=PERF.summary||{}, q=PERF.sample_quality||{};
    sum.innerHTML=[['READY signals',s.signals??0],['Closed',s.closed??0],['Win Rate',pct(s.win_rate)],['Expectancy',rval(s.expectancy_r)],['Profit Factor',Number.isFinite(+s.profit_factor)?num(s.profit_factor,2):'N/A']].map(([k,v])=>`<div class="kv"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
    quality.textContent=`Sample Quality: ${q.status||'N/A'} · ${s.closed??0}/10 для первого review · ${s.closed??0}/30 для usable`;
    note.textContent=q.message||((+s.signals||0)===0?'READY-сигналов пока нет — статистика качества еще не сформирована.':'Метрики — качество модели, не фактический P/L счета.');
    const tickers=['SBERP','VKCO','OZPH'].map(k=>`<div><b>${k}</b> — ${compactStats(PERF.by_ticker?.[k])}</div>`).join('');
    const tfs=['D1','H1','M10'].map(k=>`<div><b>${k}</b> — ${compactStats(PERF.by_tf?.[k])}</div>`).join('');
    detail.innerHTML='<div style="margin-bottom:5px;color:var(--mut)">По бумагам</div>'+tickers+'<div style="margin:8px 0 5px;color:var(--mut)">По TF</div>'+tfs;
  }

  async function loadPerf(){
    try{
      const r=await fetch('data/signal_performance.json?ts='+Date.now(),{cache:'no-store'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      const j=await r.json();
      PERF=['R0.9.0 Production Observation','R0.9.2 Production Observation'].includes(j?.release)?j:null;
    }catch(e){PERF=null;}
    drawPerf();
  }

  const oldRender=window.render;
  if(typeof oldRender==='function'){
    window.render=function(){oldRender();setTimeout(()=>{drawRisk();drawPerf();},0)};
    render=window.render;
  }

  document.title = 'TA Market Monitor · R0.9.2';
  const badge = document.querySelector('.top h1 .ok');
  if (badge) badge.textContent = 'R0.9.2';
  const footer = document.querySelector('.footer');
  if (footer) footer.innerHTML += '<br>R0.9.2: Sample Quality Gate prevents tuning on noise: <10 closed = INSUFFICIENT, 10–29 = PRELIMINARY, ≥30 = USABLE. Metrics are model quality, not actual account P/L.';
  setTimeout(function(){ if (window.J) { render(); drawRisk(); } ensurePerfBox(); loadPerf(); }, 500);
})();
