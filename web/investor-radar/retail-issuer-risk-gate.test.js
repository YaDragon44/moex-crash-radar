const assert=require('assert');
const G=require('./retail-issuer-risk-gate.js');

let r=G.assess({verified:true,revenueGrowthPct:10.5,adjustedEbitdaMarginPct:5.7,netDebtToEbitda:1.08,netProfitGrowthPct:-28.4,ratingVerified:true,rating:'AAA(RU)',ratingOutlook:'STABLE',source:'X5 H1 2026 IFRS financial results',sourceUrl:'https://www.x5.ru/ru/news/x5-obyavlyaet-o-roste-vyruchki-na-99-vo-2-kv-2026-g-rentabelnost-skorr-ebitda-do-primeneniya-msfo-ifrs-16-sostavila-60/',ratingSourceUrl:'https://acra-ratings.ru/press-releases/7029/',asOf:'2026-06-30'});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.equal(r.riskLevel,'MEDIUM');
assert.equal(r.thesisBroken,false);
assert.equal(r.coverage,'RETAIL_GROWTH_MARGIN_LEVERAGE_PROFIT_RATING');

r=G.assess({verified:true,revenueGrowthPct:-2,adjustedEbitdaMarginPct:2.5,netDebtToEbitda:3.2,netProfitGrowthPct:-60,ratingVerified:true,rating:'BBB',source:'fixture',sourceUrl:'https://example.com',ratingSourceUrl:'https://example.com/rating',asOf:'2026-06-30'});
assert.equal(r.riskLevel,'HIGH');
assert.equal(r.thesisBroken,false);

r=G.assess({verified:true,revenueGrowthPct:10,adjustedEbitdaMarginPct:6,netDebtToEbitda:1,netProfitGrowthPct:5,source:'x',sourceUrl:'https://example.com',asOf:'2026-06-30'});
assert.equal(r.status,'LOCK');
assert(r.missing.includes('credit_rating'));

console.log('R1.8.29 retail issuer risk gate tests: PASS');
