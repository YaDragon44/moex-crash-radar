// TA Market R0.8.5 production safety + execution risk patch.
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

  const oldRender=window.render;
  if(typeof oldRender==='function'){
    window.render=function(){oldRender();setTimeout(drawRisk,0)};
    render=window.render;
  }

  document.title = 'TA Market Monitor · R0.8.5';
  const badge = document.querySelector('.top h1 .ok');
  if (badge) badge.textContent = 'R0.8.5';
  const footer = document.querySelector('.footer');
  if (footer) footer.innerHTML += '<br>R0.8.5: snapshot age ≤25m is a hard READY gate; Confluence Score is conservative; position sizing uses MOEX lot size plus user-entered capital/risk/fees/slippage.';
  setTimeout(function(){ if (window.J) { render(); drawRisk(); } }, 500);
})();
