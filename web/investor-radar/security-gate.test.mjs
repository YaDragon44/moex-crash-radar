import assert from 'assert';
import fs from 'fs';
import os from 'os';
import path from 'path';
import {scan} from './security-gate.mjs';

const dir=fs.mkdtempSync(path.join(os.tmpdir(),'radar-sec-'));
try{
  const clean=path.join(dir,'clean.js');
  fs.writeFileSync(clean,"const x='https://iss.moex.com'; document.querySelector('#x').textContent='ok';\n");
  let r=scan([clean]);
  assert.equal(r.status,'PASS');
  assert.equal(r.counts.CRITICAL,0);
  assert.equal(r.counts.HIGH,0);

  const evalFile=path.join(dir,'eval.js');
  fs.writeFileSync(evalFile,"eval('2+2');\n");
  r=scan([evalFile]);
  assert.equal(r.status,'FAIL');
  assert.equal(r.counts.HIGH,1);

  const xss=path.join(dir,'xss.html');
  fs.writeFileSync(xss,"<script>const q=location.search; document.body.innerHTML=q;</script>\n");
  r=scan([xss]);
  assert.equal(r.status,'FAIL');
  assert(r.findings.some(x=>x.id==='url_input_to_html_sink_surface'&&x.severity==='HIGH'));

  const medium=path.join(dir,'medium.html');
  fs.writeFileSync(medium,"<script>document.querySelector('#x').innerHTML='<b>static</b>';</script>\n");
  r=scan([medium]);
  assert.equal(r.status,'PASS');
  assert.equal(r.counts.MEDIUM,1);

  console.log('R1.8.27 security scanner unit tests: PASS');
} finally {
  fs.rmSync(dir,{recursive:true,force:true});
}
