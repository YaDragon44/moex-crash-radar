from __future__ import annotations
import json
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain, ema, split_of
FAMILIES=['MX','SI','SBER','GD','MMU','CRU','SVU','NG','GAZP','ROSN','T']; H=(1,2,4,8); MODELS=('R0_EMA_CONTROL','R1_STRUCTURE','R2_EARLY_TREND','R3_STRUCTURE_EARLY')
def es(rows,i,n): return ema([float(x['close']) for x in rows[:i+1]],n)
def state(rows,i,m):
 c=float(rows[i]['close']); e20=es(rows,i,20);e50=es(rows,i,50);p20=es(rows,i-1,20);pc=float(rows[i-1]['close'])
 if m=='R0_EMA_CONTROL':
  if e20>e50 and e20>p20 and c>e20:return 'LONG'
  if e20<e50 and e20<p20 and c<e20:return 'SHORT'
  return 'NONE'
 prev8=rows[i-8:i]; recent4=rows[i-4:i]; prior4=rows[i-8:i-4]
 r1l=c>max(float(x['high']) for x in prev8) and min(float(x['low']) for x in recent4)>min(float(x['low']) for x in prior4)
 r1s=c<min(float(x['low']) for x in prev8) and max(float(x['high']) for x in recent4)<max(float(x['high']) for x in prior4)
 r2l=pc<=es(rows,i-1,20) and c>e20 and e20>p20 and e20/e50>=0.995
 r2s=pc>=es(rows,i-1,20) and c<e20 and e20<p20 and e20/e50<=1.005
 if m=='R1_STRUCTURE': return 'LONG' if r1l else ('SHORT' if r1s else 'NONE')
 if m=='R2_EARLY_TREND': return 'LONG' if r2l else ('SHORT' if r2s else 'NONE')
 if m=='R3_STRUCTURE_EARLY': return 'LONG' if r1l and r2l else ('SHORT' if r1s and r2s else 'NONE')
 return 'NONE'
def pf(xs):
 p=sum(x for x in xs if x>0);n=-sum(x for x in xs if x<0);return round(p/n,3) if n else (999.0 if p else None)
def stats(es,cost=5):
 xs=[x['gross_bps']-cost for x in es];n=len(xs)
 if not n:return {'n':0}
 s=sorted(xs);med=s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
 return {'n':n,'mean':round(sum(xs)/n,2),'median':round(med,2),'positive_pct':round(100*sum(x>0 for x in xs)/n,2),'profit_factor':pf(xs)}
def main():
 all_events=[];quality={}
 for fam in FAMILIES:
  try: rows,q=build_chain(fam,'2024-01-01','2026-09-01');quality[fam]=q
  except Exception as x:quality[fam]={'status':'ERROR','error':repr(x)};continue
  for m in MODELS:
   prev='NONE'
   for i in range(52,len(rows)-8):
    st=state(rows,i,m)
    # R0/R2 are states: sample transition. R1/R3 are event-like structure breaks; each qualifying bar is an event.
    fire=st in ('LONG','SHORT') and (m in ('R1_STRUCTURE','R3_STRUCTURE_EARLY') or st!=prev)
    if fire:
     for h in H:
      if rows[i+h]['secid']!=rows[i]['secid']:continue
      a=float(rows[i]['close']);b=float(rows[i+h]['close']);r=(b/a-1)*10000*(1 if st=='LONG' else -1)
      all_events.append({'model':m,'family':fam,'side':st,'split':split_of(rows[i]['begin']),'signal_time':rows[i]['begin'],'horizon':h,'gross_bps':r})
    prev=st
 report={'release':'R1.4.7','quality':quality,'models':{}}
 for m in MODELS:
  report['models'][m]={}
  for sp in ('IS','VALIDATION','OOS'):
   report['models'][m][sp]={}
   for side in ('LONG','SHORT'):
    report['models'][m][sp][side]={str(h):stats([e for e in all_events if e['model']==m and e['split']==sp and e['side']==side and e['horizon']==h]) for h in H}
  o4=[e for e in all_events if e['model']==m and e['split']=='OOS' and e['horizon']==4];v4=[e for e in all_events if e['model']==m and e['split']=='VALIDATION' and e['horizon']==4]
  om=stats(o4);vm=stats(v4);fam=[]
  for f in FAMILIES:
   z=stats([e for e in o4 if e['family']==f]);
   if z.get('n',0)>=10:fam.append(z['mean']>0)
  breadth=round(100*sum(fam)/len(fam),2) if fam else 0
  report['models'][m]['primary_4H']={'VALIDATION':vm,'OOS':om,'positive_family_share_pct':breadth,'adequately_sampled_families':len(fam)}
  report['models'][m]['gate']='CANDIDATE' if vm.get('mean',-1)>0 and om.get('mean',-1)>0 and (om.get('profit_factor') or 0)>1 and om.get('n',0)>=100 and breadth>=50 else 'NO-GO'
 Path('artifacts').mkdir(exist_ok=True);Path('artifacts/r1_4_7_regime_engine_redesign.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');Path('artifacts/r1_4_7_regime_events.json').write_text(json.dumps(all_events,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({m:{'primary':report['models'][m]['primary_4H'],'gate':report['models'][m]['gate']} for m in MODELS},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
