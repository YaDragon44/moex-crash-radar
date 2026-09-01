from __future__ import annotations
import json,math,statistics,urllib.parse,urllib.request
from collections import defaultdict,Counter
from pathlib import Path
UNIVERSE={'MX':'MXU6','Si':'SiU6','SBER':'SRU6','GD':'GDU6','BR':'BRU6','MMU':'MMU6','CRU':'CRU6','SVU':'SVU6','NG':'NGU6','GAZP':'GZU6','ROSN':'RNU6','T':'TBU6','Silver':'SLVRUBF'}
START='2026-06-01';END='2026-09-01';H=8;MODELS=('M0_FIXED_8H','M1_ATR_STOP','M2_BE_1R','M3_TREND_EXIT','M4_HYBRID');COSTS=(0,5)
def getj(u):
 r=urllib.request.Request(u,headers={'User-Agent':'moex-crash-radar/1.4.4'});return json.loads(urllib.request.urlopen(r,timeout=30).read().decode())
def candles(s):
 q=urllib.parse.urlencode({'iss.meta':'off','interval':60,'from':START,'till':END});j=getj(f'https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities/{s}/candles.json?{q}')['candles'];c=j['columns'];return [dict(zip(c,x)) for x in j['data'] if x[c.index('close')] is not None]
def ema(v,n):
 if len(v)<n:return math.nan
 e=sum(v[:n])/n;k=2/(n+1)
 for x in v[n:]:e=x*k+e*(1-k)
 return e
def trend(rows,i):
 c=[float(x['close']) for x in rows[:i+1]]
 if len(c)<51:return 'NONE'
 a,b,p=ema(c,20),ema(c,50),ema(c[:-1],20);x=c[-1]
 if a>b and a>p and x>a:return 'LONG'
 if a<b and a<p and x<a:return 'SHORT'
 return 'NONE'
def atrs(rows,n=14):
 o=[math.nan]*len(rows);trs=[]
 for i,r in enumerate(rows):
  h,l=float(r['high']),float(r['low']);pc=float(rows[i-1]['close']) if i else None;tr=h-l if i==0 else max(h-l,abs(h-pc),abs(l-pc));trs.append(tr)
  if i==n-1:o[i]=sum(trs[:n])/n
  elif i>=n:o[i]=(o[i-1]*(n-1)+tr)/n
 return o
def ret(s,e,p):
 x=(p/e-1)*10000;return x if s=='LONG' else -x
def simulate(rows,i,s,e,a,m):
 risk=1.5*a;stop=e-risk if s=='LONG' else e+risk;be_armed=False
 for k in range(1,H+1):
  b=rows[i+k];lo,hi,cl=float(b['low']),float(b['high']),float(b['close']);active=e if be_armed and m in ('M2_BE_1R','M4_HYBRID') else stop
  if m!='M0_FIXED_8H' and (lo<=active if s=='LONG' else hi>=active):return ret(s,e,active),'STOP_BE' if be_armed and active==e else 'STOP',k
  # +1R only arms break-even for the NEXT bar: conservative unknown intrabar ordering.
  if m in ('M2_BE_1R','M4_HYBRID') and not be_armed and (hi>=e+risk if s=='LONG' else lo<=e-risk):be_armed=True
  if m in ('M3_TREND_EXIT','M4_HYBRID') and trend(rows,i+k)!=s:return ret(s,e,cl),'TREND',k
  if k==H:return ret(s,e,cl),'TIME',k
 return 0,'N/A',H
def events(rows):
 aa=atrs(rows);out=[]
 for i in range(51,len(rows)-H-1):
  s=trend(rows,i)
  if s=='NONE':continue
  cl=float(rows[i]['close']);p=rows[i-1];tr=float(p['high'] if s=='LONG' else p['low'])
  if not (cl>tr if s=='LONG' else cl<tr):continue
  e=float(rows[i+1]['open']);a=aa[i]
  if not math.isfinite(a) or a<=0 or e<=0:continue
  d={'date':str(rows[i].get('begin',''))[:10],'models':{}}
  for m in MODELS:
   x,reason,bars=simulate(rows,i,s,e,a,m);d['models'][m]={'ret':x,'reason':reason,'bars':bars}
  out.append(d)
 return out
def stat(es,m,cost=0):
 xs=[x['models'][m]['ret']-cost for x in es];reasons=Counter(x['models'][m]['reason'] for x in es);bars=[x['models'][m]['bars'] for x in es]
 return {'n':len(xs),'mean':round(statistics.fmean(xs),2) if xs else None,'median':round(statistics.median(xs),2) if xs else None,'positive_pct':round(100*sum(x>0 for x in xs)/len(xs),2) if xs else None,'avg_hold_h':round(statistics.fmean(bars),2) if bars else None,'exit_mix':dict(reasons)}
def main():
 rep={'release':'R1.4.4','period':[START,END],'limitation':'current contracts, not historical roll-chain','instruments':{},'aggregate':{}};all=[]
 for label,sec in UNIVERSE.items():
  try:
   es=events(candles(sec));all+=es;mo=defaultdict(list)
   for x in es:mo[x['date'][:7]].append(x)
   rep['instruments'][label]={'n':len(es),'models':{m:stat(es,m) for m in MODELS},'monthly':{k:{m:stat(v,m) for m in MODELS} for k,v in mo.items()}}
  except Exception as x:rep['instruments'][label]={'status':'ERROR','error':repr(x)}
 rep['aggregate']={m:{str(c):stat(all,m,c) for c in COSTS} for m in MODELS};cells=[v for r in rep['instruments'].values() for v in r.get('monthly',{}).values()]
 base5=rep['aggregate']['M0_FIXED_8H']['5']['mean'];gate={}
 for m in MODELS:
  den=sum(v[m]['n']>0 for v in cells);pos=sum(v[m]['mean']>0 for v in cells if v[m]['n']>0);net=rep['aggregate'][m]['5']['mean'];hold=rep['aggregate'][m]['0']['avg_hold_h'];gate[m]={'positive_cells_pct':round(100*pos/den,2) if den else 0,'net_5bps':net,'delta_vs_fixed_5bps':round(net-base5,2),'avg_hold_h':hold,'pass':bool(m!='M0_FIXED_8H' and den and pos/den>=.70 and net>0 and net>=base5-5)}
 rep['gate']=gate;passing=[m for m,g in gate.items() if g['pass']];rep['management_status']='CANDIDATE_ONLY' if passing else 'NO_GO';rep['passing']=passing
 Path('artifacts').mkdir(exist_ok=True);Path('artifacts/r1_4_4_exit_management.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf8')
 lines=['# R1.4.4 Exit & Trade Management','',f'Signals: **{len(all)}**','', '| Model | Net @5bps | Δ vs fixed | Positive cells | Avg hold | Gate |','|---|---:|---:|---:|---:|---|']
 for m,g in gate.items():lines.append(f"| {m} | {g['net_5bps']} | {g['delta_vs_fixed_5bps']} | {g['positive_cells_pct']}% | {g['avg_hold_h']}h | {'PASS' if g['pass'] else 'FAIL'} |")
 lines+=['',f"Management status: **{rep['management_status']}**",f"Passing candidates: **{', '.join(passing) if passing else 'none'}**",'', '> PASS means candidate evidence only because this replay is not yet a historical roll-chain.']
 Path('artifacts/r1_4_4_exit_management.md').write_text('\n'.join(lines),encoding='utf8');print('\n'.join(lines))
if __name__=='__main__':main()
