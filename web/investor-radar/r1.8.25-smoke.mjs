import { chromium } from 'playwright';

const base=process.env.SMOKE_BASE||'http://127.0.0.1:8765';
const url=`${base}/r1.8.24.html`;

async function openPage(context,{abortMoex=false}={}){
  if(abortMoex){
    await context.route('https://iss.moex.com/**',route=>route.abort('failed'));
  }
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForFunction(()=>{
    const s=document.querySelector('#status')?.textContent||'';
    return s && !s.includes('Загрузка MOEX');
  },{timeout:30000});
  const result=await page.evaluate(()=>({
    status:document.querySelector('#status')?.textContent||'',
    blockers:document.querySelector('#blockers')?.textContent||'',
    grid:document.querySelector('#grid')?.textContent||'',
    details:document.querySelector('#details')?.textContent||''
  }));
  return {page,errors,result};
}

const browser=await chromium.launch({headless:true});
try{
  // Live browser smoke: the page must render and leave loading state without JS errors.
  const liveContext=await browser.newContext();
  const live=await openPage(liveContext);
  if(live.errors.length) throw new Error('pageerror: '+live.errors.join(' | '));
  if(!/PARTIAL|VERIFIED|LOCK/.test(live.result.status)) throw new Error('unexpected live status: '+live.result.status);
  if(!live.result.grid.includes('Текущая цена')) throw new Error('SBER UI grid missing');
  if(!live.result.blockers.includes('Блокирующие данные')) throw new Error('blockers section missing');
  console.log('R1.8.25 live browser smoke: PASS',live.result.status);
  await liveContext.close();

  // Forced MOEX outage: fail-closed behavior must still render, never white-screen or active recommendation.
  const failContext=await browser.newContext();
  const fail=await openPage(failContext,{abortMoex:true});
  if(fail.errors.length) throw new Error('pageerror during MOEX outage: '+fail.errors.join(' | '));
  if(!/PARTIAL|LOCK/.test(fail.result.status)) throw new Error('MOEX outage did not fail closed: '+fail.result.status);
  if(!fail.result.status.includes('НАБЛЮДАТЬ')) throw new Error('MOEX outage produced active action: '+fail.result.status);
  if(!fail.result.blockers.includes('Недостаточно данных для обоснованного вывода')) throw new Error('insufficient-data explanation missing');
  console.log('R1.8.25 MOEX outage browser smoke: PASS',fail.result.status);
  await failContext.close();
} finally {
  await browser.close();
}
