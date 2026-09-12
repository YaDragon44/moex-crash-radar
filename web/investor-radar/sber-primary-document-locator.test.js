'use strict';
const assert=require('assert');
const Gate=require('./sber-primary-document-locator.js');

let r=Gate.current();
assert.equal(r.status,'PARTIAL');
assert.equal(r.verified,false);
assert(r.missing.includes('document_content_extraction'));
assert(r.missing.includes('attributable_common_equity'));
assert(r.documents.annualReport2025.url.includes('sber-ar-2025-ru.pdf'));
assert.equal(r.documents.issuerReport2025.published,'2026-03-30');

const src='https://www.sberbank.com/common/img/uploaded/_new_site/com/gosa2026/sber-ar-2025-ru.pdf';
const evidence={};
for(const t of Gate.REQUIRED_TARGETS){evidence[t]={primary:true,sourceUrl:src,locator:'fixture:p1',value:'fixture'};}
r=Gate.assess({documents:Gate.DOCUMENTS,extracted:true,targetEvidence:evidence});
assert.equal(r.status,'VERIFIED');
assert.equal(r.verified,true);
assert.deepEqual(r.missing,[]);

console.log('R1.8.41 SBER primary document locator gate: PASS');
