from __future__ import annotations
import json, statistics
from collections import defaultdict
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain
from run_r1_4_7_regime_engine_redesign import state

START='2022-01-01'; END='2026-09-01'; H=(1,2,4,8); COSTS=(0.0,2.0,5.0,10.0)
FAMILIES=('SBER','GAZP','ROSN','T'); MODELS=('R0_EMA_CONTROL','R2_EARLY_TREND')

def split(ts):
 y=int(ts[:4]); return 'DEVELOPMENT' if y<=2024 else ('VALIDATION' if y==2025 else 'OOS')
def half(ts): return f"{ts[:4]}-H{1 if int(ts[5:7])<=6 else 2}"
def pf(xs):
 p=sum(x for x in xs if x>0); n=-sum(x for x in xs if x<0)
 return round(p/n,3) if n else (999.0 if p else None)
def stats(xs):
 if not xs:return {'n':0}
 s=sorted(xs); n=len(xs); trim=s[1:-1] if n>=5 else s
 return {'n':n,'mean':round(sum(xs)/n,2),'median':round(statistics.median(xs),2),'positive_pct':round(100*sum(x>0 for x in xs)/n,2),'profit_factor':pf(xs),'trimmed_mean':round(sum(trim)/len(trim),2),'sum':round(sum(xs),2)}
def collect():
 events=[]; quality={}
 for fam in FAMILIES:
  try: rows,q=build_chain(fam,START,END); quality[fam]=q
  except Exception as exc: quality[fam]={'status':'ERROR','error':repr(exc)}; continue
  for model in MODELS:
   prev='NONE'
   for i in range(52,len(rows)-max(H)):
    st=state(rows,i,model)
    fire=st=='SHORT' and st!=prev
    if fire:
     for h in H:
      if rows[i+h]['secid']!=rows[i]['secid']:continue
      a=float(rows[i]['close']); b=float(rows[i+h]['close']); gross=(a/b-1)*10000
      events.append({'model':model,'family':fam,'signal_time':rows[i]['begin'],'split':split(rows[i]['begin']),'year':rows[i]['begin'][:4],'half':half(rows[i]['begin']),'horizon':h,'gross_bps':gross,'secid':rows[i]['secid']})
    prev=st
 return events,quality

def grouped(es,key,cost):
 d=defaultdict(list)
 for e in es:d[e[key]].append(e['gross_bps']-cost)
 return {k:stats(v) for k,v in sorted(d.items())}
def sensitivity(es,cost):
 vals=[e['gross_bps']-cost for e in es]; base=stats(vals)
 if not es:return {'base':base}
 best=max(es,key=lambda e:e['gross_bps']-cost)
 leave_best=stats([e['gross_bps']-cost for e in es if e is not best])
 fams=sorted({e['family'] for e in es}); loo={f:stats([e['gross_bps']-cost for e in es if e['family']!=f]) for f in fams}
 pos=[(e['family'],e['gross_bps']-cost) for e in es if e['gross_bps']-cost>0]; total=sum(v for _,v in pos); by=defaultdict(float)
 for f,v in pos:by[f]+=v
 shares=sorted(by.values(),reverse=True)
 return {'base':base,'best_event':best,'leave_best_event_out':leave_best,'leave_one_family_out':loo,'top1_positive_pnl_share_pct':round(100*shares[0]/total,2) if total and shares else None,'top3_positive_pnl_share_pct':round(100*sum(shares[:3])/total,2) if total and shares else None}
def evaluate(model, events):
 primary=[e for e in events if e['model']==model and e['horizon']==4]
 out={'costs':{},'by_family':{},'by_year':{},'by_half':{}}
 for cost in COSTS:
  c=str(int(cost))
  out['costs'][c]={sp:stats([e['gross_bps']-cost for e in primary if e['split']==sp]) for sp in ('DEVELOPMENT','VALIDATION','OOS')}
 oos=[e for e in primary if e['split']=='OOS']; out['sensitivity_5bps']=sensitivity(oos,5.0)
 for fam in FAMILIES:
  out['by_family'][fam]={sp:stats([e['gross_bps']-5 for e in primary if e['family']==fam and e['split']==sp]) for sp in ('DEVELOPMENT','VALIDATION','OOS')}
 out['by_year']=grouped(primary,'year',5.0); out['by_half']=grouped(primary,'half',5.0)
 v=out['costs']['5']['VALIDATION']; o=out['costs']['5']['OOS']; o10=out['costs']['10']['OOS']; sens=out['sensitivity_5bps']
 pos_fams=sum(1 for fam in FAMILIES if out['by_family'][fam]['OOS'].get('mean',-1)>0 and out['by_family'][fam]['OOS'].get('n',0)>0)
 loo_ok=all(z.get('mean',-1)>0 for z in sens.get('leave_one_family_out',{}).values()) if sens.get('leave_one_family_out') else False
 conc=sens.get('top1_positive_pnl_share_pct'); lb=sens.get('leave_best_event_out',{})
 chronological=[z for k,z in out['by_half'].items() if k.startswith('2026-') and z.get('n',0)>0]
 chrono_ok=sum(1 for z in chronological if z.get('mean',-1)>0)>=2 if len(chronological)>1 else False
 checks={'validation_positive':v.get('mean',-1)>0 and (v.get('profit_factor') or 0)>1,'oos_positive':o.get('mean',-1)>0 and (o.get('profit_factor') or 0)>1,'oos_n_min':o.get('n',0)>=15,'positive_families_2plus':pos_fams>=2,'leave_best_positive':lb.get('mean',-1)>0,'leave_one_family_positive':loo_ok,'concentration_le_60':conc is not None and conc<=60,'oos_10bps_nonnegative':o10.get('mean',-1)>=0,'chronology_multi_period':chrono_ok}
 out['checks']=checks; out['positive_oos_families']=pos_fams
 if all(checks.values()): status='RESEARCH_CANDIDATE'
 elif o.get('n',0)<15 or not chrono_ok: status='INSUFFICIENT_EVIDENCE'
 else: status='REJECTED_NON_ROBUST'
 out['status']=status
 return out

def main():
 events,quality=collect(); models={m:evaluate(m,events) for m in MODELS}; survivors=[m for m,z in models.items() if z['status']=='RESEARCH_CANDIDATE']
 report={'release':'R1.4.8.1','period':{'start':START,'end':END},'universe':FAMILIES,'direction':'SHORT','models':models,'quality':quality,'gate':{'survivors':survivors,'survivor_count':len(survivors),'status':'RESEARCH_CANDIDATE' if survivors else 'TECHNICAL_ONLY_STOP','production':'NO-GO','next':'INDEPENDENT_MARKET_SPECIFIC_VALIDATION' if survivors else 'OI_POSITIONING_CONTEXT'}}
 Path('artifacts').mkdir(exist_ok=True); Path('artifacts/r1_4_8_1_equity_short_robustness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); Path('artifacts/r1_4_8_1_equity_short_events.json').write_text(json.dumps(events,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({'gate':report['gate'],'models':{m:{'status':z['status'],'cost5':z['costs']['5'],'cost10_oos':z['costs']['10']['OOS'],'checks':z['checks'],'positive_oos_families':z['positive_oos_families'],'sensitivity':z['sensitivity_5bps']} for m,z in models.items()}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
