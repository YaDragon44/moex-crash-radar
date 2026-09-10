from __future__ import annotations
import json, math
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain, ema, split_of
FAMILIES=['MX','SI','SBER','GD','MMU','CRU','SVU','NG','GAZP','ROSN','T']; H=(1,2,4,8)
def trend(rows,i):
 c=[float(x['close']) for x in rows[:i+1]]; e20=ema(c,20);e50=ema(c,50);p20=ema(c[:-1],20)
 if e20>e50 and e20>p20 and c[-1]>e20:return 'LONG'
 if e20<e50 and e20<p20 and c[-1]<e20:return 'SHORT'
 return 'NONE'
def pf(xs):
 pos=sum(x for x in xs if x>0);neg=-sum(x for x in xs if x<0)
 return round(pos/neg,3) if neg else (999.0 if pos else None)
def stats(es,cost=5):
 xs=[e['gross_bps']-cost for e in es]; n=len(xs)
 if not n:return {'n':0}
 s=sorted(xs);med=s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
 return {'n':n,'mean':round(sum(xs)/n,2),'median':round(med,2),'positive_pct':round(100*sum(x>0 for x in xs)/n,2),'profit_factor':pf(xs)}
def main():
 events=[];quality={}
 for fam in FAMILIES:
  try:rows,q=build_chain(fam,'2024-01-01','2026-09-01');quality[fam]=q
  except Exception as x:quality[fam]={'status':'ERROR','error':repr(x)};continue
  prev='NONE'
  for i in range(51,len(rows)-8):
   st=trend(rows,i)
   if st in ('LONG','SHORT') and st!=prev:
    for h in H:
     if i+h>=len(rows) or rows[i+h]['secid']!=rows[i]['secid']:continue
     a=float(rows[i]['close']);b=float(rows[i+h]['close']);r=(b/a-1)*10000*(1 if st=='LONG' else -1)
     events.append({'family':fam,'contract':rows[i]['secid'],'side':st,'signal_time':rows[i]['begin'],'split':split_of(rows[i]['begin']),'horizon':h,'gross_bps':r})
   prev=st
 report={'release':'R1.4.6.3','quality':quality,'aggregate':{},'eligibility':{}}
 for sp in ('IS','VALIDATION','OOS'):
  report['aggregate'][sp]={}
  for side in ('LONG','SHORT'):
   report['aggregate'][sp][side]={str(h):stats([e for e in events if e['split']==sp and e['side']==side and e['horizon']==h]) for h in H}
 for fam in FAMILIES:
  report['eligibility'][fam]={}
  for side in ('LONG','SHORT'):
   cells={}
   for sp in ('VALIDATION','OOS'):
    cells[sp]={str(h):stats([e for e in events if e['family']==fam and e['side']==side and e['split']==sp and e['horizon']==h]) for h in H}
   # 4H is the primary eligibility horizon, pre-specified as middle actionable horizon.
   v=cells['VALIDATION']['4'];o=cells['OOS']['4']
   if v.get('n',0)>=30 and o.get('n',0)>=30 and v.get('mean',0)<=0 and o.get('mean',0)<=0:cl='INELIGIBLE'
   elif v.get('mean',-1)>0 and o.get('mean',-1)>0 and (o.get('profit_factor') or 0)>1 and o.get('n',0)>=30:cl='ELIGIBLE_CANDIDATE'
   else:cl='RESEARCH_ONLY'
   report['eligibility'][fam][side]={'classification':cl,'primary_horizon':'4H','metrics':cells}
 Path('artifacts').mkdir(exist_ok=True);Path('artifacts/r1_4_6_3_trend_market_eligibility.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');Path('artifacts/r1_4_6_3_state_events.json').write_text(json.dumps(events,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({'aggregate':report['aggregate'],'classification':{f:{s:report['eligibility'][f][s]['classification'] for s in ('LONG','SHORT')} for f in FAMILIES}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
