// TA Market R0.8.5 execution risk block.
(function(){
  const LS='ta_market_risk_v085';
  const money=x=>Number.isFinite(+x)?(+x).toLocaleString('ru-RU',{maximumFractionDigits:0})+' ₽':'N/A';
  const num=(x,d=2)=>Number.isFinite(+x)?(+x).toLocaleString('ru-RU',{minimumFractionDigits:d,maximumFractionDigits:d}):'N/A';
  function loadCfg(){try{return {...{capital:0,riskPct:0,commissionPct:0,slippagePct:0},...JSON.parse(localStorage.getItem(LS)||'{}')}}catch(e){return{capital:0,riskPct:0,commissionPct:0,slippagePct:0}}}
  function saveCfg(c){localStorage.setItem(LS,JSON.stringify(c))}
  function calc(a){
    const c=loadCfg(), md=J?.securities?.[sel]?.marketdata||{}, lot=Math.max(1,Math.floor(+md.LOTSIZE||1));
    const entry=+a?.plan?.entry, stop=+a?.plan?.stop;
    if(!(c.capital>0&&c.riskPct>0&&Number.isFinite(entry)&&Number.isFinite(stop)&&entry>0)) return {lot,valid:false};
    const allowed=c.capital*c.riskPct/100;
    const gross=Math.abs(entry-stop);
    const friction=entry*(2*c.commissionPct+2*c.slippagePct)/100;
    const perShare=gross+friction;
    const perLot=perShare*lot;
    let lots=perLot>0?Math.floor(allowed/perLot):0;
    const maxLots=Math.floor(c.capital/(entry*lot));
    lots=Math.max(0,Math.min(lots,maxLots));
    const shares=lots*lot;
    return {lot,valid:true,allowed,gross,friction,perShare,perLot,lots,shares,position:shares*entry,moneyRisk:lots*perLot};
  }
  function ensure(){
    if(document.getElementById('riskbox'))return;
    const aside=document.querySelector('aside.panel'); if(!aside)return;
    const box=document.createElement('div'); box.id='riskbox';
    box.innerHTML='<div class="section">Риск и размер позиции</div><div class="trade" id="riskinputs"></div><div class="trade" id="riskout"></div><div class="gate" id="risknote">Введите капитал и риск % — без них размер позиции не рассчитывается.</div>';
    aside.appendChild(box);
  }
  function draw(){
    ensure(); if(!window.J||!window.sel)return;
    const c=loadCfg(), a=window.analyze?.(sel), r=calc(a);
    const inp=document.getElementById('riskinputs'), out=document.getElementById('riskout'); if(!inp||!out)return;
    const field=(k,label,step)=>`<label class="kv"><div class="k">${label}</div><input data-risk="${k}" type="number" min="0" step="${step}" value="${c[k]||0}" style="width:100%;margin-top:5px;background:#0a1119;color:var(--tx);border:1px solid var(--ln);border-radius:6px;padding:6px"></label>`;
    inp.innerHTML=field('capital','Капитал ₽','1000')+field('riskPct','Риск %','0.1')+field('commissionPct','Комиссия % / сторона','0.001')+field('slippagePct','Проскальзывание % / сторона','0.001');
    inp.querySelectorAll('[data-risk]').forEach(el=>el.onchange=()=>{const n=+el.value||0;c[el.dataset.risk]=Math.max(0,n);saveCfg(c);draw()});
    out.innerHTML=[['Лот MOEX',r.lot],['Допустимый риск',r.valid?money(r.allowed):'N/A'],['Риск/акция',r.valid?num(r.perShare,2)+' ₽':'N/A'],['Риск/лот',r.valid?money(r.perLot):'N/A'],['Лотов',r.valid?r.lots:'N/A'],['Акций',r.valid?r.shares:'N/A'],['Размер позиции',r.valid?money(r.position):'N/A'],['Денежный риск',r.valid?money(r.moneyRisk):'N/A']].map(([k,v])=>`<div class="kv"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
    const note=document.getElementById('risknote');
    note.textContent=r.valid?(r.lots>0?'Без плеча · комиссия и проскальзывание учтены на входе и выходе.':'Корректный стоп/издержки не позволяют открыть даже 1 лот при заданном риске.'):'Введите капитал и риск % — без них размер позиции не рассчитывается.';
  }
  const oldRender=window.render;
  if(typeof oldRender==='function'){window.render=function(){oldRender();setTimeout(draw,0)};render=window.render;}
  setTimeout(draw,700);
})();
