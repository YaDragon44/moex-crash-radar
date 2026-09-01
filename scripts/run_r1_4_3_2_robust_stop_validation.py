from __future__ import annotations

import json, math, statistics, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

UNIVERSE={'MX':'MXU6','Si':'SiU6','SBER':'SRU6','GD':'GDU6','BR':'BRU6','MMU':'MMU6','CRU':'CRU6','SVU':'SVU6','NG':'NGU6','GAZP':'GZU6','ROSN':'RNU6','T':'TBU6','Silver':'SLVRUBF'}
START='2026-06-01'; END='2026-09-01'; H=8
STOPS=('NO_STOP','SIGNAL_CANDLE','ATR_1_0','ATR_1_5','SWING_3')
COST_BPS=(0,2,5,10)

def getj(url):
 req=urllib.request.Request(url,headers={'User-Agent':'moex-crash-radar/1.4.3.2'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
def candles(secid):
 q=urllib.parse.urlencode({'iss.meta':'off','interval':60,'from':START,'till':END})
 j=getj(f'https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities/{secid}/candles.json?{q}')['candles']; c=j['columns']
 return [dict(zip(c,x)) for x in j['data'] if x[c.index('close')] is not None]
def ema(v,n):
 if len(v)<n:return math.nan
 e=sum(v[:n])/n;k=2/(n+1)
 for x in v[n:]:e=x*k+e*(1-k)
 return e
def atrs(rows,n=14):
 out=[math.nan]*len(rows);trs=[]
 for i,r in enumerate(rows):
  h,l=float(r['high']),float(r['low']); pc=float(rows[i-1]['close']) if i else None
  tr=h-l if i==0 else max(h-l,abs(h-pc),abs(l-pc));trs.append(tr)
  if i==n-1:out[i]=sum(trs[:n])/n
  elif i>=n:out[i]=(out[i-1]*(n-1)+tr)/n
 return out
def side(rows,i):
 c=[float(r['close']) for r in rows[:i+1]]
 if len(c)<51:return 'NONE'
 a,b,p=ema(c,20),ema(c,50),ema(c[:-1],20);x=c[-1]
 if a>b and a>p and x>a:return 'LONG'
 if a<b and a<p and x<a:return 'SHORT'
 return 'NONE'
def sr(s,e,p):
 x=(p/e-1)*10000;return x if s=='LONG' else -x
def sl(rows,i,e,a,s,m):
 if m=='SIGNAL_CANDLE':return float(rows[i]['low'] if s=='LONG' else rows[i]['high'])
 if m=='ATR_1_0':return e-a if s=='LONG' else e+a
 if m=='ATR_1_5':return e-1.5*a if s=='LONG' else e+1.5*a
 w=rows[max(0,i-2):i+1];return min(float(x['low']) for x in w) if s=='LONG' else max(float(x['high']) for x in w)
def events(rows):
 aa=atrs(rows);out=[]
 for i in range(51,len(rows)-H-1):
  s=side(rows,i)
  if s=='NONE':continue
  prev=rows[i-1];cl=float(rows[i]['close']);tr=float(prev['high'] if s=='LONG' else prev['low'])
  if not (cl>tr if s=='LONG' else cl<tr):continue
  e=float(rows[i+1]['open']);a=aa[i]
  if not math.isfinite(a) or a<=0 or e<=0:continue
  fut=rows[i+1:i+1+H]; raw=sr(s,e,float(fut[-1]['close']))
  mfe=max(sr(s,e,float(x['high'] if s=='LONG' else x['low'])) for x in fut);mae=min(sr(s,e,float(x['low'] if s=='LONG' else x['high'])) for x in fut)
  d={'date':str(rows[i].get('begin',''))[:10],'side':s,'raw':raw,'mfe':mfe,'mae':mae,'atr_pct':100*a/e,'models':{}}
  for m in STOPS:
   if m=='NO_STOP':d['models'][m]={'exit':raw,'hit':False,'risk':None};continue
   z=sl(rows,i,e,a,s,m);risk=abs(z/e-1)*10000;hit=False;ex=raw
   for bar in fut:
    if (float(bar['low'])<=z if s=='LONG' else float(bar['high'])>=z):hit=True;ex=-risk;break
   d['models'][m]={'exit':ex,'hit':hit,'risk':risk}
  out.append(d)
 return out
def stats(es,m,cost=0):
 xs=[e['models'][m]['exit']-cost for e in es]
 if not xs:return {'n':0}
 hits=[e['models'][m]['hit'] for e in es]
 return {'n':len(xs),'mean':round(statistics.fmean(xs),2),'median':round(statistics.median(xs),2),'positive_pct':round(100*sum(x>0 for x in xs)/len(xs),2),'stop_hit_pct':round(100*sum(hits)/len(hits),2) if m!='NO_STOP' else None}
def main():
 report={'release':'R1.4.3.2','period':[START,END],'method':'current-contract robustness extension; not roll-chain','instruments':{},'aggregate':{}}
 all=[]
 for label,sec in UNIVERSE.items():
  try:
   es=events(candles(sec));all+=es; months=defaultdict(list)
   for e in es:months[e['date'][:7]].append(e)
   report['instruments'][label]={'secid':sec,'n':len(es),'mae_mean':round(statistics.fmean(e['mae'] for e in es),2) if es else None,'mfe_mean':round(statistics.fmean(e['mfe'] for e in es),2) if es else None,'models':{m:stats(es,m) for m in STOPS},'monthly':{mo:{m:stats(v,m) for m in STOPS} for mo,v in months.items()}}
  except Exception as x:report['instruments'][label]={'secid':sec,'status':'ERROR','error':repr(x)}
 report['aggregate']['n']=len(all);report['aggregate']['models']={m:{str(c):stats(all,m,c) for c in COST_BPS} for m in STOPS}
 # Robust candidate: positive gross mean in >=70% non-empty instrument-month cells and aggregate survives 5 bps cost.
 cells=[]
 for r in report['instruments'].values():
  for mo,v in r.get('monthly',{}).items():cells.append(v)
 gates={}
 for m in STOPS:
  pos=sum(v[m].get('mean',-1)>0 for v in cells if v[m].get('n',0));den=sum(v[m].get('n',0)>0 for v in cells);agg5=report['aggregate']['models'][m]['5'].get('mean',-999)
  gates[m]={'positive_cells_pct':round(100*pos/den,2) if den else 0,'aggregate_mean_after_5bps':agg5,'pass':bool(den and pos/den>=.70 and agg5>0)}
 report['gate']=gates;report['production_stop']='NO_GO' if not any(gates[m]['pass'] for m in STOPS if m!='NO_STOP') else 'CANDIDATE_ONLY'
 Path('artifacts').mkdir(exist_ok=True);Path('artifacts/r1_4_3_2_robust_stop_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 lines=['# R1.4.3.2 Robust Stop Validation','',f"Period: {START} → {END}",f"Signals: **{len(all)}**",'', '| Model | Mean gross | Mean after 5 bps | Positive instrument-month cells | Gate |','|---|---:|---:|---:|---|']
 for m in STOPS:
  g=gates[m];lines.append(f"| {m} | {report['aggregate']['models'][m]['0'].get('mean')} | {report['aggregate']['models'][m]['5'].get('mean')} | {g['positive_cells_pct']}% | {'PASS' if g['pass'] else 'FAIL'} |")
 lines+=['',f"Production hard-stop: **{report['production_stop']}**",'', '> Limitation: this release still uses current contract IDs, not a historical roll-chain. A PASS is therefore candidate evidence, not production approval.']
 Path('artifacts/r1_4_3_2_robust_stop_validation.md').write_text('\n'.join(lines),encoding='utf-8');print('\n'.join(lines))
if __name__=='__main__':main()
