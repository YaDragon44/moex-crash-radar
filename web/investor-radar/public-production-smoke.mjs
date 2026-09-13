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
  const tickers=await page.$$eval('#cards .card .ticker',els=>els.map(e=>e.textContent?.trim()));
  const expected=['SBER','YDEX','X5','MOEX'];
  if(JSON.stringify(tickers)!==JSON.stringify(expected)) throw new Error(`unexpected cards: ${JSON.stringify(tickers)}`);
  if(pageErrors.length) throw new Error('pageerror: '+pageErrors.join(' | '));

  const gate=await page.locator('#gate').textContent();
  console.log('Investor Radar public browser smoke: PASS', {tickers,gate,failedRequests:failed.length});
} finally {
  await browser.close();
}
