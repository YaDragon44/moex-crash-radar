import { chromium } from 'playwright';

const url='https://yadragon44.github.io/moex-crash-radar/investor-radar/index.html?v='+Date.now();
const browser=await chromium.launch({headless:true});
try {
  const page=await browser.newPage();
  const pageErrors=[];
  const failed=[];
  page.on('pageerror',e=>pageErrors.push(String(e)));
  page.on('requestfailed',r=>failed.push(`${r.url()} :: ${r.failure()?.errorText||'failed'}`));
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});

  await page.waitForFunction(()=>document.querySelectorAll('#cards .card').length===4,{timeout:15000});
  await page.waitForFunction(()=>{
    const gate=(document.querySelector('#gate')?.textContent||'').trim();
    return gate && !gate.includes('Загрузка MOEX');
  },{timeout:45000});

  const tickers=await page.$$eval('#cards .card .ticker',els=>els.map(e=>e.textContent?.trim()));
  const expected=['SBER','YDEX','X5','MOEX'];
  if(JSON.stringify(tickers)!==JSON.stringify(expected)) throw new Error(`unexpected cards: ${JSON.stringify(tickers)}`);
  if(pageErrors.length) throw new Error('pageerror: '+pageErrors.join(' | '));

  const gate=(await page.locator('#gate').textContent())?.trim()||'';
  if(!gate.includes('MOEX quotes:')) throw new Error('final gate summary missing: '+gate);

  const cards=await page.$$eval('#cards .card',els=>els.map(el=>({
    ticker:el.getAttribute('data-ticker'),
    text:(el.textContent||'').replace(/\s+/g,' ').trim()
  })));

  for(const card of cards){
    if(!card.text.includes('Recommendation gate:')) throw new Error(`${card.ticker}: recommendation gate missing`);
    if(!card.text.includes('Full risk gate')) throw new Error(`${card.ticker}: risk gate missing`);
    if(!card.text.includes('Valuation gate')) throw new Error(`${card.ticker}: valuation gate missing`);
    const locked=card.text.includes('Recommendation gate: LOCK');
    if(locked && !card.text.includes('НАБЛЮДАТЬ')) throw new Error(`${card.ticker}: fail-closed violation`);
  }

  console.log('Investor Radar R1.8.52 production functional snapshot: PASS');
  console.log('FINAL GATE:',gate);
  for(const card of cards) console.log('CARD:',JSON.stringify(card));
  console.log('FAILED REQUESTS:',failed.length,failed);
} finally {
  await browser.close();
}
