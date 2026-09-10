from __future__ import annotations
import json, statistics
from collections import defaultdict
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain
from run_r1_4_7_regime_engine_redesign import state, FAMILIES, MODELS

START='2022-01-01'; END='2026-09-01'; H=(1,2,4,8); COST=5.0
CLASSES={'INDEX':['MX','MMU'],'FX':['SI','CRU'],'EQUITY':['SBER','GAZP','ROSN','T'],'COMMODITY':['GD','SVU','NG']}
FAMILY_CLASS={f:c for c,fs in CLASSES.items() for f in fs}

def split(ts):
 y=int(ts[:4]); return 'DEVELOPMENT' if y<=2024 else ('VALIDATION' if y==2025 else 'OOS')
def half(ts): return f"{ts[:4]}-H{1 if int(ts[5:7])<=6 else 2}"
def pf(xs):
 p=sum(x for x in xs if x>0); n=-sum(x for x in xs if x<0)
 return round(p/n,3) if n else (999.0 if p else None)
def stats(xs):
 if not xs:return {'n':0}
 s=sorted(xs); n=len(xs); trim=s[1:-1] if n>=5 else s
 return {'n':n,'mean':round(sum(xs)/n,2),'median':round(statistics.median(xs),2),'positive_pct':round(100*sum(x>0 for x in xs)/n,2),'profit_factor':pf(xs),'trimmed_mean':round(sum(trim)/len(trim),2)}
def collect():
 events=[]; quality={}
 for fam in FAMILIES:
  try: rows,q=build_chain(fam,START,END); quality[fam]=q
  except Exception as exc: quality[fam]={'status':'ERROR','error':repr(exc)}; continue
  for model in MODELS:
   prev='NONE'
   for i in range(52,len(rows)-8):
    st=state(rows,i,model)
    fire=st in ('LONG','SHORT') and (model in ('R1_STRUCTURE','R3_STRUCTURE_EARLY') or st!=prev)
    if fire:
     for h in H:
      if rows[i+h]['secid']!=rows[i]['secid']: continue
      a=float(rows[i]['close']); b=float(rows[i+h]['close']); gross=(b/a-1)*10000*(1 if st=='LONG' else -1)
      events.append({'model':model,'family':fam,'market_class':FAMILY_CLASS[fam],'side':st,'signal_time':rows[i]['begin'],'split':split(rows[i]['begin']),'half':half(rows[i]['begin']),'horizon':h,'net_bps':gross-COST})
    prev=st
 return events,quality

def contribution(es):
 pos=[e for e in es if e['net_bps']>0]; total=sum(e['net_bps'] for e in pos)
 by=defaultdict(float)
 for e in pos: by[e['family']]+=e['net_bps']
 share=max(by.values())/total*100 if total and by else None
 return round(share,2) if share is not None else None

def classify(v,o,families):
 if o.get('n',0)<15:return 'RESEARCH_ONLY'
 if v.get('mean',-1)>0 and o.get('mean',-1)>0 and (o.get('profit_factor') or 0)>1:return 'CANDIDATE'
 if v.get('n',0)>=10 and o.get('n',0)>=10 and v.get('mean',1)<=0 and o.get('mean',1)<=0:return 'REJECTED'
 return 'RESEARCH_ONLY'

def main():
 events,quality=collect(); p=[e for e in events if e['horizon']==4]
 report={'release':'R1.4.8','period':{'start':START,'end':END},'quality':quality,'classes':CLASSES,'cost_bps':COST,'segments':{},'family_direction':{},'gate':{}}
 candidates=[]
 for cls,fams in CLASSES.items():
  report['segments'][cls]={}
  for side in ('LONG','SHORT'):
   report['segments'][cls][side]={}
   for model in MODELS:
    v_es=[e for e in p if e['market_class']==cls and e['side']==side and e['model']==model and e['split']=='VALIDATION']
    o_es=[e for e in p if e['market_class']==cls and e['side']==side and e['model']==model and e['split']=='OOS']
    v=stats([e['net_bps'] for e in v_es]); o=stats([e['net_bps'] for e in o_es]); status=classify(v,o,fams)
    represented={e['family'] for e in o_es}; pos_fams={f for f in represented if stats([e['net_bps'] for e in o_es if e['family']==f]).get('mean',-1)>0}
    conc=contribution(o_es); halfs=defaultdict(list)
    for e in o_es:halfs[e['half']].append(e['net_bps'])
    z={'validation':v,'oos':o,'status':status,'represented_families':len(represented),'positive_families':len(pos_fams),'max_positive_family_contribution_pct':conc,'oos_by_half':{k:stats(x) for k,x in sorted(halfs.items())}}
    # strict class candidate gate
    enough=o.get('n',0)>=15 and (len(fams)<2 or len(represented)>=2) and (conc is None or conc<=60)
    if status=='CANDIDATE' and enough: z['eligibility']='CANDIDATE'; candidates.append((cls,side,model))
    else:z['eligibility']='NO-GO'
    report['segments'][cls][side][model]=z
 for fam in FAMILIES:
  report['family_direction'][fam]={}
  for side in ('LONG','SHORT'):
   report['family_direction'][fam][side]={}
   for model in MODELS:
    report['family_direction'][fam][side][model]={sp:stats([e['net_bps'] for e in p if e['family']==fam and e['side']==side and e['model']==model and e['split']==sp]) for sp in ('DEVELOPMENT','VALIDATION','OOS')}
 report['gate']={'candidate_segments':[{'market_class':a,'side':b,'model':c} for a,b,c in candidates],'candidate_count':len(candidates),'status':'SEGMENTS_FOUND' if candidates else 'NO_TECHNICAL_SEGMENT','production':'NO-GO','next':'MARKET_SPECIFIC_VALIDATION' if candidates else 'OI_POSITIONING_CONTEXT'}
 Path('artifacts').mkdir(exist_ok=True); Path('artifacts/r1_4_8_market_specific_regime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); Path('artifacts/r1_4_8_regime_events.json').write_text(json.dumps(events,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({'gate':report['gate'],'segments':report['segments']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
