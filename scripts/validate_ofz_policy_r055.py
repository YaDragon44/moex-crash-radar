#!/usr/bin/env python3
import json
from pathlib import Path
from ofz_strategy_engine import compare_strategies

SRC=Path('web/ofz-radar/data/current.json')
OUT=Path('web/ofz-radar/data/policy-validation.json')

SCENARIOS={
 'FAST_FALL':[16.41,14.0,12.0,10.0,8.0,5.0],
 'HIGH_FOR_LONGER':[16.41,16.0,15.5,15.0,14.5,14.0],
 'FALL_REVERSAL':[16.41,14.0,11.0,9.0,12.0,16.0],
 'STRESS_RISE':[16.41,17.0,18.0,19.0,18.0,17.0],
}
POLICIES={
 'BASELINE_100_60_25':{'A':1.0,'B':1.0,'C':1.0,'D':.60,'E':.25},
 'LATE_EXIT_100_80_50':{'A':1.0,'B':1.0,'C':1.0,'D':.80,'E':.50},
 'MILD_EXIT_100_90_65':{'A':1.0,'B':1.0,'C':1.0,'D':.90,'E':.65},
 'EARLY_CUT_100_85_60_25':{'A':1.0,'B':1.0,'C':.85,'D':.60,'E':.25},
}

def main():
 j=json.loads(SRC.read_text(encoding='utf-8'));p=j['portfolio'];b=j['bonds'];vd=j['valuationDate']
 results=[]
 for pname,policy in POLICIES.items():
  rows=[]
  for sname,path in SCENARIOS.items():
   c=compare_strategies(p,b,vd,path,policy)
   if not c.get('ready'): raise SystemExit(f'{pname}/{sname}: not ready')
   h,a=c['buyHold'],c['active']
   rows.append({'scenario':sname,'deltaTerminal':c['deltaTerminal'],'deltaCagr':c['deltaCagr'],'drawdownImprovement':a['maxDrawdown']-h['maxDrawdown'],'activeMaxDrawdown':a['maxDrawdown'],'holdMaxDrawdown':h['maxDrawdown'],'turnoverPct':a['turnoverPct'],'activeTerminal':a['terminalValue'],'holdTerminal':h['terminalValue']})
  avg_delta=sum(r['deltaTerminal'] for r in rows)/len(rows)
  avg_dd=sum(r['drawdownImprovement'] for r in rows)/len(rows)
  avg_turn=sum(r['turnoverPct'] for r in rows)/len(rows)
  fast=next(r for r in rows if r['scenario']=='FAST_FALL');rev=next(r for r in rows if r['scenario']=='FALL_REVERSAL')
  results.append({'name':pname,'policy':policy,'scenarios':rows,'summary':{'avgDeltaTerminal':avg_delta,'avgDrawdownImprovement':avg_dd,'avgTurnoverPct':avg_turn,'fastFallDelta':fast['deltaTerminal'],'reversalDrawdownImprovement':rev['drawdownImprovement']}})
 # Pareto: maximize avg terminal delta and avg DD improvement, minimize turnover
 for x in results:
  dominated=False
  xs=x['summary']
  for y in results:
   if y is x: continue
   ys=y['summary']
   no_worse=ys['avgDeltaTerminal']>=xs['avgDeltaTerminal'] and ys['avgDrawdownImprovement']>=xs['avgDrawdownImprovement'] and ys['avgTurnoverPct']<=xs['avgTurnoverPct']
   strictly=ys['avgDeltaTerminal']>xs['avgDeltaTerminal'] or ys['avgDrawdownImprovement']>xs['avgDrawdownImprovement'] or ys['avgTurnoverPct']<xs['avgTurnoverPct']
   if no_worse and strictly: dominated=True;break
  x['pareto']=not dominated
 pareto=[x['name'] for x in results if x['pareto']]
 # No automatic production change: candidate is informational until historical validation.
 out={'version':'0.5.5','sourceVersion':j.get('version'),'valuationDate':vd,'status':'PASS','policies':results,'paretoPolicies':pareto,'decision':'NO_PRODUCTION_CHANGE','reason':'Scenario matrix is insufficient to justify a production threshold change. Use Pareto set as candidates for historical validation.','assumptions':{'protectiveSleeveYield':0.0,'taxes':False,'commissions':False,'slippage':False}}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('OFZ R0.5.5 POLICY COMPARISON: PASS')
 print('PARETO:', ', '.join(pareto))
 for x in results:
  s=x['summary'];print(f"{x['name']}: avgDelta={s['avgDeltaTerminal']:.0f} avgDDimp={s['avgDrawdownImprovement']:.4f} turnover={s['avgTurnoverPct']:.2f} pareto={x['pareto']}")

if __name__=='__main__': main()
