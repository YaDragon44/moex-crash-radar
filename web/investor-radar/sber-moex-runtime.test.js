'use strict';
const assert=require('assert');
const R=require('./sber-moex-runtime.js');

const candles={candles:{columns:['begin','close'],data:[
 ['2025-12-01 00:00:00',290.1],
 ['2025-12-29 00:00:00',299.5],
 ['2025-12-30 00:00:00',300.05]
]}};
const ye=R.parseYearEnd(candles,2025);
assert.strictEqual(ye.verified,true);
assert.strictEqual(ye.date,'2025-12-30');
assert.strictEqual(ye.close,300.05);
assert.ok(R.candleUrl('SBER',2025).includes('from=2025-12-01'));
assert.ok(R.candleUrl('SBER',2025).includes('till=2025-12-31'));
assert.ok(R.candleUrl('SBER',2025).includes('interval=24'));

const quote={marketdata:{columns:['SECID','LAST','LCURRENTPRICE','UPDATETIME'],data:[
 ['VTBR',82.5,null,'18:39:00']
]}};
const q=R.parseQuote(quote,'VTBR');
assert.strictEqual(q.verified,true);
assert.strictEqual(q.price,82.5);

const q2=R.parseQuote({marketdata:{columns:['SECID','LAST','LCURRENTPRICE'],data:[['T',null,3210]]}},'T');
assert.strictEqual(q2.price,3210);

assert.strictEqual(R.parseYearEnd({candles:{columns:['begin','close'],data:[]}},2024).verified,false);
assert.strictEqual(R.parseQuote({marketdata:{columns:['SECID','LAST'],data:[['VTBR',null]]}},'VTBR').verified,false);

(async()=>{
 const calls=[];
 const fake=async url=>({ok:true,status:200,json:async()=>{
  calls.push(url);
  if(url.includes('candles.json')){
   const y=Number((url.match(/from=(\d{4})-/)||[])[1]);
   return {candles:{columns:['begin','close'],data:[[`${y}-12-30 00:00:00`,100+y-2023]]}};
  }
  const ticker=url.includes('/VTBR.json')?'VTBR':'T';
  return {marketdata:{columns:['SECID','LAST','LCURRENTPRICE','UPDATETIME'],data:[[ticker,ticker==='VTBR'?80:3200,null,'18:40:00']]}};
 }});
 const out=await R.collect(fake);
 assert.strictEqual(out.verified,true);
 assert.strictEqual(out.historical.length,3);
 assert.strictEqual(out.peers.VTBR.price,80);
 assert.strictEqual(out.peers.T.price,3200);
 assert.strictEqual(calls.length,5);
 console.log('SBER MOEX Runtime: PASS');
})().catch(e=>{console.error(e);process.exit(1);});
