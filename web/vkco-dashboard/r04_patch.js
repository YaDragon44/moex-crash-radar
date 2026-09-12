(()=>{
  const NS='http://www.w3.org/2000/svg';
  const TA='../ta-market/data/current.json';
  const LIVE='https://raw.githubusercontent.com/YaDragon44/moex-crash-radar/vkco-live/status.json';
  const q=s=>document.querySelector(s);
  const fmt=n=>Number.isFinite(+n)?new Intl.NumberFormat('ru-RU',{maximumFractionDigits:2}).format(+n):'—';
  function candleObj(z){
    if(!z||Array.isArray(z))return null;
    const close=+(z.close??z.CLOSE),open=+(z.open??z.OPEN),high=+(z.high??z.HIGH),low=+(z.low??z.LOW),volume=+(z.volume??z.VOLUME??0);
    const time=z.end??z.END??z.begin??z.BEGIN;
    return [close,open,high,low].every(Number.isFinite)?{close,open,high,low,volume:Number.isFinite(volume)?volume:0,time}:null;
  }
  function svgEl(name,attrs={}){const e=document.createElementNS(NS,name);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));return e}
  function marker(svg,x,y,label,color){
    svg.appendChild(svgEl('circle',{cx:x,cy:y,r:5,fill:color,stroke:'#071016','stroke-width':2}));
    const t=svgEl('text',{x:x+8,y:y-8,fill:color,'font-size':12,'font-weight':800});t.textContent=label;svg.appendChild(t);
  }
  function ensureVolumePanel(){
    if(q('#volumeChart'))return;
    const price=q('#priceChart'); if(!price)return;
    const wrap=price.parentElement;
    const vol=document.createElementNS(NS,'svg');vol.id='volumeChart';vol.setAttribute('viewBox','0 0 1200 130');vol.setAttribute('preserveAspectRatio','none');vol.style.width='100%';vol.style.height='130px';vol.style.display='block';vol.style.borderTop='1px solid rgba(118,144,158,.12)';wrap.appendChild(vol);
    const legend=q('.legend'); if(legend){const s=document.createElement('span');s.innerHTML='<b style="background:var(--muted)"></b>Volume';legend.appendChild(s)}
  }
  async function render(){
    ensureVolumePanel();
    const price=q('#priceChart'),vol=q('#volumeChart'); if(!price||!vol)return;
    try{
      const [tr,lr]=await Promise.all([fetch(TA+'?v='+Date.now(),{cache:'no-store'}),fetch(LIVE+'?v='+Date.now(),{cache:'no-store'})]);
      if(!tr.ok||!lr.ok)throw Error('data');
      const tj=await tr.json(),live=await lr.json();
      const sec=(tj.securities||{}).VKCO||{},raw=sec.raw||{},src=raw.M10||raw.m10||[];
      const candles=Array.isArray(src)?src.map(candleObj).filter(Boolean).slice(-72):[];
      if(!candles.length)return;
      vol.innerHTML='';
      const W=1200,H=130,L=54,R=22,T=10,B=20,maxV=Math.max(...candles.map(c=>c.volume),1),step=(W-L-R)/Math.max(candles.length,1),bar=Math.max(2,step*.58);
      candles.forEach((c,i)=>{const x=L+i*step+step/2,y=T+(maxV-c.volume)*(H-T-B)/maxV,h=H-B-y;vol.appendChild(svgEl('rect',{x:x-bar/2,y,width:bar,height:Math.max(1,h),rx:1,fill:c.close>=c.open?'#285b49':'#5b3038',opacity:.86}))});
      const avg=candles.reduce((a,c)=>a+c.volume,0)/candles.length;
      const yAvg=T+(maxV-avg)*(H-T-B)/maxV;vol.appendChild(svgEl('line',{x1:L,y1:yAvg,x2:W-R,y2:yAvg,stroke:'#76909e','stroke-width':1,'stroke-dasharray':'6 5'}));
      const lab=svgEl('text',{x:W-R-4,y:yAvg-4,fill:'#76909e','font-size':11,'text-anchor':'end'});lab.textContent='AVG VOL '+fmt(avg);vol.appendChild(lab);
      const status=(live.position||{}).status||(live.trade||{}).status||'WAIT';
      const m=(live.market||{}),p=(live.position||{}),t=(live.trade||{});
      const vals=candles.flatMap(c=>[c.low,c.high]);let min=Math.min(...vals),max=Math.max(...vals),pad=Math.max((max-min)*.12,.25);min-=pad;max+=pad;
      const x=i=>54+i*(1200-54-22)/Math.max(candles.length-1,1),y=v=>18+(max-v)*(360-18-28)/(max-min);
      const lastX=x(candles.length-1),lastY=y(candles.at(-1).close);
      if(status==='READY')marker(price,lastX,lastY,'READY','#39e69d');
      if(['OPEN','TP1','TP2','TRAILING'].includes(status))marker(price,lastX,y(Number.isFinite(+p.entry)?+p.entry:candles.at(-1).close),'OPEN','#58c7ff');
      if(String(status).startsWith('CLOSED')||['MANUAL_EXIT','INVALIDATED'].includes(status))marker(price,lastX,lastY,'CLOSED','#a78bfa');
      const st=q('#chartState'); if(st)st.textContent=(st.textContent||'').replace(/ · VOL.*$/,'')+' · VOL '+fmt(candles.at(-1).volume)+' · AVG '+fmt(avg);
    }catch(e){/* core chart remains usable */}
  }
  window.addEventListener('load',()=>{render();setInterval(render,60000)});
})();