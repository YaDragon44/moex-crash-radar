from __future__ import annotations

import argparse, json, math, statistics, urllib.parse, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

MONTH_CODES={3:'H',6:'M',9:'U',12:'Z'}
PREFIXES={'MX':'MX','SI':'Si','SBER':'SR','GD':'GD','MMU':'MM','CRU':'CR','SVU':'SV','NG':'NG','GAZP':'GZ','ROSN':'RN','T':'TB'}
COSTS=(0,2,5,10)

def getj(url):
 req=urllib.request.Request(url,headers={'User-Agent':'moex-crash-radar/1.4.5'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

def candles(secid,start,end):
 q=urllib.parse.urlencode({'iss.meta':'off','interval':60,'from':start,'till':end})
 j=getj(f'https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities/{secid}/candles.json?{q}')['candles']; c=j['columns']
 return [dict(zip(c,x)) for x in j['data'] if x[c.index('close')] is not None]

def third_thursday(y,m):
 d=date(y,m,1)
 while d.weekday()!=3:d+=timedelta(days=1)
 return d+timedelta(days=14)

def sub_weekdays(d,n):
 while n:
  d-=timedelta(days=1)
  if d.weekday()<5:n-=1
 return d

def contracts(label,start,end,roll_days=5):
 p=PREFIXES[label]; sd,ed=date.fromisoformat(start),date.fromisoformat(end); out=[]
 for y in range(sd.year-1,ed.year+2):
  for m,code in MONTH_CODES.items():
   exp=third_thursday(y,m); roll=sub_weekdays(exp,roll_days)
   if exp>=sd-timedelta(days=120) and roll<=ed+timedelta(days=120):out.append({'secid':f'{p}{code}{str(y)[-1]}','expiry':exp,'roll':roll})
 return sorted(out,key=lambda x:x['expiry'])

def build_chain(label,start,end,fetcher=candles,roll_days=5):
 cs=contracts(label,start,end,roll_days); sd,ed=date.fromisoformat(start),date.fromisoformat(end); raw={}; missing=[]
 for c in cs:
  fs=max(sd,c['expiry']-timedelta(days=130)); fe=min(ed,c['expiry']+timedelta(days=7))
  if fs>fe:continue
  try:r=fetcher(c['secid'],fs.isoformat(),fe.isoformat())
  except Exception:r=[]
  if not r:missing.append(c['secid']);continue
  raw[c['secid']]={x['begin']:x for x in r}
 times=sorted({t for v in raw.values() for t in v}); out=[]
 for ts in times:
  d=datetime.fromisoformat(ts).date()
  if d<sd or d>ed:continue
  active=next((c for c in cs if d<=c['roll']),cs[-1] if cs else None)
  if not active:continue
  row=raw.get(active['secid'],{}).get(ts)
  if row is not None:out.append({**row,'secid':active['secid'],'roll_date':active['roll'].isoformat()})
 return out,{'planned':[c['secid'] for c in cs],'used':sorted({r['secid'] for r in out}),'missing':missing,'bars':len(out)}

def ema(v,n):
 if len(v)<n:return math.nan
 e=sum(v[:n])/n;k=2/(n+1)
 for x in v[n:]:e=x*k+e*(1-k)
 return e

def atrs(rows,n=14):
 out=[math.nan]*len(rows); trs=[]
 for i,r in enumerate(rows):
  h,l=float(r['high']),float(r['low']); pc=float(rows[i-1]['close']) if i else None
  tr=h-l if i==0 else max(h-l,abs(h-pc),abs(l-pc)); trs.append(tr)
  if i==n-1:out[i]=sum(trs[:n])/n
  elif i>=n:out[i]=(out[i-1]*(n-1)+tr)/n
 return out

def side(rows,i):
 c=[float(r['close']) for r in rows[:i+1]]
 if len(c)<51:return 'NONE'
 e20,e50,p20=ema(c,20),ema(c,50),ema(c[:-1],20); x=c[-1]
 if e20>e50 and e20>p20 and x>e20:return 'LONG'
 if e20<e50 and e20<p20 and x<e20:return 'SHORT'
 return 'NONE'

def ret_bps(s,e,p):
 x=(p/e-1)*10000
 return x if s=='LONG' else -x

def split_of(ts):
 y=int(str(ts)[:4])
 return 'IS' if y<=2024 else ('VALIDATION' if y==2025 else 'OOS')

def events(rows,h=8,atr_mult=1.5):
 aa=atrs(rows); out=[]
 for i in range(51,len(rows)-1):
  s=side(rows,i)
  if s=='NONE':continue
  prev=rows[i-1]; cl=float(rows[i]['close']); trig=float(prev['high'] if s=='LONG' else prev['low'])
  if not (cl>trig if s=='LONG' else cl<trig):continue
  if rows[i+1]['secid']!=rows[i]['secid']:continue
  e=float(rows[i+1]['open']); a=aa[i]
  if not math.isfinite(a) or a<=0 or e<=0:continue
  stop=e-atr_mult*a if s=='LONG' else e+atr_mult*a; fut=[]
  for j in range(i+1,min(i+1+h,len(rows))):
   if rows[j]['secid']!=rows[i]['secid']:break
   fut.append(rows[j])
  if not fut:continue
  exitp=float(fut[-1]['close']); reason='TIME'; hit_idx=None
  mfe=-1e99; mae=1e99
  for k,b in enumerate(fut):
   mfe=max(mfe,ret_bps(s,e,float(b['high'] if s=='LONG' else b['low'])))
   mae=min(mae,ret_bps(s,e,float(b['low'] if s=='LONG' else b['high'])))
   if (float(b['low'])<=stop if s=='LONG' else float(b['high'])>=stop):exitp=stop;reason='STOP';hit_idx=k;break
  gross=ret_bps(s,e,exitp); hold=(hit_idx+1) if hit_idx is not None else len(fut)
  out.append({'family':rows[i]['secid'][:-2],'contract':rows[i]['secid'],'side':s,'signal_time':rows[i]['begin'],'entry_time':rows[i+1]['begin'],'exit_time':fut[hold-1]['begin'],'signal_close':cl,'trigger':trig,'entry':e,'stop':stop,'exit':exitp,'atr14':a,'exit_reason':reason,'gross_bps':gross,'net_bps':{str(c):gross-c for c in COSTS},'mae_bps':mae,'mfe_bps':mfe,'mae_atr':mae/(a/e*10000),'mfe_atr':mfe/(a/e*10000),'holding_bars':hold,'split':split_of(rows[i]['begin'])})
 return out

def metrics(es,cost=5):
 xs=[e['gross_bps']-cost for e in es]
 if not xs:return {'n':0}
 gp=sum(x for x in xs if x>0); gl=-sum(x for x in xs if x<0); eq=0;peak=0;dd=0
 for x in xs:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
 pf=gp/gl if gl>0 else None
 return {'n':len(xs),'mean':round(statistics.fmean(xs),2),'median':round(statistics.median(xs),2),'positive_pct':round(100*sum(x>0 for x in xs)/len(xs),2),'profit_factor':round(pf,3) if pf is not None else None,'cum_bps':round(sum(xs),2),'max_drawdown_bps':round(dd,2),'recovery_factor':round(sum(xs)/dd,3) if dd>0 else None,'stop_hit_pct':round(100*sum(e['exit_reason']=='STOP' for e in es)/len(es),2),'avg_hold':round(statistics.fmean(e['holding_bars'] for e in es),2)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--start',default='2024-01-01');p.add_argument('--end',default='2026-09-01');p.add_argument('--families',default='MX,SI,SBER,GD,MMU,CRU,SVU,NG,GAZP,ROSN,T');a=p.parse_args()
 report={'release':'R1.4.5','period':[a.start,a.end],'baseline':'Trend+Trigger / next-open / ATR1.5 / max 8H','families':{},'aggregate':{},'quality':{}}
 alltr=[]
 for label in [x.strip().upper() for x in a.families.split(',') if x.strip()]:
  try:
   rows,diag=build_chain(label,a.start,a.end); es=events(rows); alltr+=es
   report['families'][label]={'quality':diag,'trades':len(es),'splits':{s:{str(c):metrics([e for e in es if e['split']==s],c) for c in COSTS} for s in ('IS','VALIDATION','OOS')}}
  except Exception as x:report['families'][label]={'status':'ERROR','error':repr(x)}
 report['aggregate']={s:{str(c):metrics([e for e in alltr if e['split']==s],c) for c in COSTS} for s in ('IS','VALIDATION','OOS')}
 qcells=[]
 for label,r in report['families'].items():
  o=r.get('splits',{}).get('OOS',{}).get('5',{}); 
  if o.get('n',0):qcells.append(o.get('mean',-1)>0)
 oos=report['aggregate']['OOS']['5']; positive_share=100*sum(qcells)/len(qcells) if qcells else 0
 ng=report['families'].get('NG',{}).get('splits',{}).get('OOS',{}).get('5',{})
 report['gate']={'oos_mean_after_5bps':oos.get('mean'),'oos_pf':oos.get('profit_factor'),'positive_family_share_pct':round(positive_share,2),'ng_oos_mean_after_5bps':ng.get('mean'),'status':'GO' if oos.get('n',0)>=100 and oos.get('mean',-1)>0 and (oos.get('profit_factor') or 0)>1 and positive_share>=60 else 'NO-GO'}
 Path('artifacts').mkdir(exist_ok=True);Path('artifacts/r1_4_5_trade_ledger.json').write_text(json.dumps(alltr,ensure_ascii=False),encoding='utf-8');Path('artifacts/r1_4_5_complete_backtest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report['gate'],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
