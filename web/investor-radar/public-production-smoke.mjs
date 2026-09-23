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

  await page.waitForFunction(()=>document.querySelectorAll('#cards .card').length===7,{timeout:15000});
  await page.waitForFunction(()=>{
    const gate=(document.querySelector('#gate')?.textContent||'').trim();
    return gate && !gate.includes('Загрузка MOEX');
  },{timeout:45000});

  const tickers=await page.$$eval('#cards .card .ticker',els=>els.map(e=>e.textContent?.trim()));
  const expected=['SBER','YDEX','X5','MOEX','VKCO','AFLT','GAZP'];
  if(JSON.stringify(tickers)!==JSON.stringify(expected)) throw new Error(`unexpected cards: ${JSON.stringify(tickers)}`);
  if(pageErrors.length) throw new Error('pageerror: '+pageErrors.join(' | '));

  const title=(await page.locator('h1').textContent())?.trim()||'';
  if(title!=='Investor Radar R1.8.54') throw new Error('unexpected production version: '+title);

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
    if(card.text.includes('issuer_risk_provenance_missing')) throw new Error(`${card.ticker}: issuer provenance wiring regression`);
    const locked=card.text.includes('Recommendation gate: LOCK');
    if(locked && !card.text.includes('НАБЛЮДАТЬ')) throw new Error(`${card.ticker}: fail-closed violation`);
  }

  const sber=cards.find(c=>c.ticker==='SBER');
  if(!sber) throw new Error('SBER card missing');
  if(sber.text.includes('verified_fundamentals')) throw new Error('SBER verified fundamentals integration regression');
  if(!/Auto historical P\/E3/.test(sber.text)) throw new Error('SBER historical P/E registry/runtime integration did not produce 3 observations: '+sber.text);

  console.log('Investor Radar R1.8.54 seven-ticker production snapshot: PASS');
  console.log('FINAL GATE:',gate);
  for(const card of cards) console.log('CARD:',JSON.stringify(card));
  console.log('FAILED REQUESTS:',failed.length,failed);
} finally {
  await browser.close();
}
