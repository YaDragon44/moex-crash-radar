const assert=require('assert');
const fs=require('fs');
const path=require('path');
const root=__dirname;
const modules=[
 'recommendation-engine.js','risk-layer.js','issuer-risk-registry.js','sanctions-regulatory-registry.js',
 'bank-issuer-risk-gate.js','retail-issuer-risk-gate.js','exchange-issuer-risk-gate.js','tech-issuer-risk-gate.js',
 'production-readiness-gate.js'
];
for(const f of modules){
 const s=fs.readFileSync(path.join(root,f),'utf8');
 assert(!/require\(['"](?!\.\/)/.test(s),`${f}: external runtime dependency forbidden`);
 assert(!/from\s+['"][^.]|import\s+['"][^.]/.test(s),`${f}: external ES module dependency forbidden`);
 assert(!/express\(|fastify\(|next\//i.test(s),`${f}: backend/framework dependency forbidden in static Investor Radar core`);
}
const networkModules=modules.filter(f=>/fetch\(|XMLHttpRequest|axios/i.test(fs.readFileSync(path.join(root,f),'utf8')));
assert.deepEqual(networkModules,[],`decision/risk core must be pure; network found in ${networkModules.join(',')}`);
const ui=fs.readFileSync(path.join(root,'r1.8.24.html'),'utf8');
assert(!/ReactDOM|createRoot\(|new Vue\(|Angular/i.test(ui),'R1.8 UI should remain static/simple without a new frontend framework');
console.log('R1.8.36 architecture simplicity gate: PASS');
