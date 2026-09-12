(() => {
  const liveUrl = 'https://raw.githubusercontent.com/YaDragon44/moex-crash-radar/vkco-live/status.json';
  const states = ['WAIT','READY','OPEN','TP1','TP2','TRAILING','CLOSED'];
  const activeMap = {CLOSED_PROFIT:'CLOSED',CLOSED_STOP:'CLOSED',MANUAL_EXIT:'CLOSED',INVALIDATED:'CLOSED'};
  const fmt = n => Number.isFinite(+n) ? new Intl.NumberFormat('ru-RU',{maximumFractionDigits:2}).format(+n) : '—';
  const set = (id, value, cls) => { const e=document.getElementById(id); if(!e)return; e.textContent=value; if(cls)e.className=cls; };

  function paintSteps(status){
    const current = activeMap[status] || status || 'WAIT';
    const idx = Math.max(0, states.indexOf(current));
    document.querySelectorAll('#steps .step').forEach((el,i)=>{
      el.classList.remove('active','done');
      if(i < idx) el.classList.add('done');
      if(i === idx) el.classList.add('active');
    });
  }

  function actionFor(status, reason){
    if(status === 'READY') return 'READY подтверждён. Проверить план, риск и только затем принимать решение о входе.';
    if(['OPEN','TP1','TP2','TRAILING'].includes(status)) return 'Сопровождать модельную позицию по стопу и целям. Не расширять риск.';
    if(status && status.startsWith('CLOSED')) return 'Модельная сделка закрыта. Ждать новый независимый READY.';
    if(reason === 'EVENT_RISK') return 'WAIT: событие блокирует вход. Ждать снятия Event Risk.';
    if(reason === 'MARKET_FILTER') return 'WAIT: фильтр IMOEX не подтверждает LONG.';
    if(reason === 'STALE_OR_MARKET_CLOSED') return 'Рынок закрыт или данные устарели. Новых действий нет.';
    return 'Наблюдать. Ждать качественный READY.';
  }

  async function loadLive(){
    try{
      const r=await fetch(liveUrl+'?v='+Date.now(),{cache:'no-store'});
      if(!r.ok) throw Error(String(r.status));
      const j=await r.json();
      const t=j.trade||{}; const p=j.position||{}; const m=j.market||{}; const jr=j.journal||{}; const risk=j.risk||{};
      const status=p.status||t.status||'WAIT';
      set('tradeStatus',status, status==='READY'?'big ok':(['OPEN','TP1','TP2','TRAILING'].includes(status)?'big cyan':status.startsWith('CLOSED')?'big violet':'big cyan'));
      set('tradeReason',t.reason||p.last_event||'—');
      paintSteps(status);
      set('action',actionFor(status,t.reason));
      if(m.price!=null) set('price',fmt(m.price)+' ₽');
      if(m.candle_end) set('priceTime',m.candle_end+' · age '+fmt(m.age_min)+' min');
      set('closed',`${jr.trades||0} / 10`);
      set('gate10',(jr.trades||0)>=10?'READY':'WAIT',(jr.trades||0)>=10?'v ok':'v warn');
      set('gate20',(jr.trades||0)>=20?'READY':'WAIT',(jr.trades||0)>=20?'v ok':'v warn');
      const overall=document.getElementById('overall');
      const liveOk=j.health==='OK';
      overall.innerHTML=`<span class="dot ${liveOk?'ok':'warn'}"></span>${liveOk?'LIVE STATE ONLINE':'LIVE STATE DEGRADED'}`;
      overall.className='badge '+(liveOk?'ok':'warn');
      const detail=[];
      if(p.entry!=null) detail.push(`Entry ${fmt(p.entry)} ₽`);
      if(p.stop!=null) detail.push(`Stop ${fmt(p.stop)} ₽`);
      if(p.tp1!=null) detail.push(`TP1 ${fmt(p.tp1)} ₽`);
      if(p.tp2!=null) detail.push(`TP2 ${fmt(p.tp2)} ₽`);
      if(p.tp3!=null) detail.push(`TP3 ${fmt(p.tp3)} ₽`);
      if(detail.length) set('tradeReason',(t.reason||p.last_event||'MODEL POSITION')+' · '+detail.join(' · '));
      const updated=document.getElementById('updated');
      const riskTxt=risk.max_risk_rub!=null?` · риск ${fmt(risk.max_risk_rub)} ₽`:'';
      updated.textContent=`Live state: ${j.generated_at||'—'}${riskTxt} · auto-refresh 60s`;
    }catch(e){
      const o=document.getElementById('overall');
      if(o){o.innerHTML='<span class="dot warn"></span>LIVE STATE UNAVAILABLE';o.className='badge warn';}
    }
  }

  setTimeout(loadLive,300);
  setInterval(loadLive,60000);
})();
