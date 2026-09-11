import fs from 'fs';
import path from 'path';

const root=process.cwd();
const scope=[path.join(root,'web','investor-radar'),path.join(root,'.github','workflows')];
const skipNames=new Set(['node_modules','.git']);
const textExt=new Set(['.js','.mjs','.html','.md','.yml','.yaml','.json','.py','.sh','.txt']);

function productionFile(p){
  const n=path.basename(p);
  return !/\.test\.(?:js|mjs)$/.test(n) && n!=='security-gate.mjs';
}
function walk(p,out=[]){
  if(!fs.existsSync(p)) return out;
  const st=fs.statSync(p);
  if(st.isDirectory()){
    for(const name of fs.readdirSync(p)){
      if(skipNames.has(name)) continue;
      walk(path.join(p,name),out);
    }
  } else if(textExt.has(path.extname(p).toLowerCase())&&productionFile(p)) out.push(p);
  return out;
}

const rules=[
  {id:'private_key',severity:'CRITICAL',re:/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/},
  {id:'github_pat',severity:'CRITICAL',re:/\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b/},
  {id:'telegram_bot_token',severity:'CRITICAL',re:/\b\d{8,12}:[A-Za-z0-9_-]{30,}\b/},
  {id:'t_invest_token',severity:'CRITICAL',re:/\bt\.[A-Za-z0-9_-]{35,}\b/},
  {id:'dangerous_eval',severity:'HIGH',re:/\beval\s*\(|\bnew\s+Function\s*\(/},
  {id:'document_write',severity:'HIGH',re:/\bdocument\.write\s*\(/},
  {id:'insecure_remote_http',severity:'HIGH',re:/http:\/\/(?!127\.0\.0\.1|localhost)[A-Za-z0-9.-]+/}
];

function scanText(file,text){
  const findings=[];
  for(const rule of rules){
    if(rule.re.test(text)) findings.push({file:path.relative(root,file),severity:rule.severity,id:rule.id});
  }
  const hasLocation=/\b(?:location\.(?:search|hash)|URLSearchParams\s*\()/i.test(text);
  const hasHtmlSink=/\.innerHTML\s*=|insertAdjacentHTML\s*\(/.test(text);
  if(hasLocation&&hasHtmlSink) findings.push({file:path.relative(root,file),severity:'HIGH',id:'url_input_to_html_sink_surface'});
  if(hasHtmlSink) findings.push({file:path.relative(root,file),severity:'MEDIUM',id:'html_sink_review_required'});
  return findings;
}

export function scan(files){
  const findings=[];
  for(const file of files){
    let text='';
    try{text=fs.readFileSync(file,'utf8');}catch{continue;}
    findings.push(...scanText(file,text));
  }
  const unique=[...new Map(findings.map(x=>[`${x.file}|${x.severity}|${x.id}`,x])).values()];
  const counts={CRITICAL:0,HIGH:0,MEDIUM:0,LOW:0};
  for(const f of unique) counts[f.severity]=(counts[f.severity]||0)+1;
  return {status:(counts.CRITICAL===0&&counts.HIGH===0)?'PASS':'FAIL',verified:counts.CRITICAL===0&&counts.HIGH===0,counts,findings:unique};
}

if(import.meta.url===`file://${process.argv[1]}`){
  const files=scope.flatMap(x=>walk(x));
  const result=scan(files);
  console.log(JSON.stringify({scope:files.length,...result},null,2));
  if(!result.verified) process.exit(1);
}
