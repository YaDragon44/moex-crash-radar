#!/usr/bin/env python3
import json
from pathlib import Path
from ofz_strategy_engine import compare_strategies

SRC=Path('web/ofz-radar/data/current.json')
OUT=Path('web/ofz-radar/data/strategy-validation.json')

SCENARIOS={
  'FAST_FALL':[16.41,14.0,12.0,10.0,8.0,5.0],
  'HIGH_FOR_LONGER':[16.41,16.0,15.5,15.0,14.5,14.0],
  'FALL_REVERSAL':[16.41,14.0,11.0,9.0,12.0,16.0],
  'STRESS_RISE':[16.41,17.0,18.0,19.0,18.0,17.0],
}

def main():
    j=json.loads(SRC.read_text(encoding='utf-8'))
    p=j['portfolio']; bonds=j['bonds']; vd=j['valuationDate']
    rows=[]
    for name,path in SCENARIOS.items():
        c=compare_strategies(p,bonds,vd,path)
        if not c.get('ready'):
            raise SystemExit(f'{name}: simulator not ready')
        h=c['buyHold']; a=c['active']
        row={
          'name':name,'path':path,
          'buyHoldTerminal':h['terminalValue'],'activeTerminal':a['terminalValue'],
          'deltaTerminal':c['deltaTerminal'],'deltaCagr':c['deltaCagr'],
          'buyHoldMaxDrawdown':h['maxDrawdown'],'activeMaxDrawdown':a['maxDrawdown'],
          'drawdownImprovement':a['maxDrawdown']-h['maxDrawdown'],
          'activeTurnoverPct':a['turnoverPct'],'activeActions':a['actions'],
          'returnWinner':'ACTIVE' if c['deltaTerminal']>0 else 'BUY_HOLD' if c['deltaTerminal']<0 else 'TIE',
          'riskWinner':'ACTIVE' if a['maxDrawdown']>h['maxDrawdown'] else 'BUY_HOLD' if a['maxDrawdown']<h['maxDrawdown'] else 'TIE',
        }
        rows.append(row)
    by={r['name']:r for r in rows}
    structural={
      'fastFallDoesNotArtificiallyFavorActive':by['FAST_FALL']['deltaTerminal']<=0,
      'highForLongerNearHold':abs(by['HIGH_FOR_LONGER']['deltaTerminal'])<0.05*p['capital'],
      'stressRiseRevealsNoAutomaticProtection':by['STRESS_RISE']['activeMaxDrawdown']<=by['STRESS_RISE']['buyHoldMaxDrawdown']+0.002,
      'allFinite':all(abs(r['deltaTerminal'])<10*p['capital'] and -1<r['buyHoldMaxDrawdown']<=0 and -1<r['activeMaxDrawdown']<=0 for r in rows),
    }
    status='PASS' if all(structural.values()) else 'HOLD'
    conclusion=(
      'Current A/B/C=100%, D=60%, E=25% rule is a profit-locking / duration-reduction policy after yields fall; '
      'it is not a hedge against an initial rise in long OFZ yields. Validate thresholds before treating it as a risk-control rule.'
    )
    out={'version':'0.5.4','sourceVersion':j.get('version'),'valuationDate':vd,'capital':p['capital'],'status':status,'scenarios':rows,'structuralChecks':structural,'conclusion':conclusion,'assumptions':{'protectiveSleeveYield':0.0,'taxes':False,'commissions':False,'slippage':False}}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'OFZ R0.5.4 STRATEGY VALIDATION: {status}')
    for r in rows:
        print(f"{r['name']}: delta={r['deltaTerminal']:.0f} dd_hold={r['buyHoldMaxDrawdown']:.4f} dd_active={r['activeMaxDrawdown']:.4f} winner={r['returnWinner']}/{r['riskWinner']}")
    if status!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
