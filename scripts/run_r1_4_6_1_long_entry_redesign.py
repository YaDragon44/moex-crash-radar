from __future__ import annotations
import json, math
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain, atrs, side, ret_bps, split_of, metrics

FAMILIES=['MX','SI','SBER','GD','MMU','CRU','SVU','NG','GAZP','ROSN','T']
VARIANTS=('L0_CONTROL','L1_HOLD','L2_RETEST')

def replay(rows,variant,h=8,atr_mult=1.5):
 aa=atrs(rows); out=[]
 for i in range(51,len(rows)-2):
  s=side(rows,i)
  if s=='NONE': continue
  prev=rows[i-1]; cl=float(rows[i]['close']); level=float(prev['high'] if s=='LONG' else prev['low'])
  base=(cl>level if s=='LONG' else cl<level)
  if not base: continue
  sig=i
  if s=='LONG' and variant!='L0_CONTROL':
   j=i+1
   if rows[j]['secid']!=rows[i]['secid'] or side(rows,j)!='LONG': continue
   if variant=='L1_HOLD' and not float(rows[j]['close'])>level: continue
   if variant=='L2_RETEST' and not (float(rows[j]['low'])<=level and float(rows[j]['close'])>level): continue
   sig=j
  entry_i=sig+1
  if entry_i>=len(rows) or rows[entry_i]['secid']!=rows[sig]['secid']: continue
  e=float(rows[entry_i]['open']); a=aa[sig]
  if not math.isfinite(a) or a<=0 or e<=0: continue
  stop=e-atr_mult*a if s=='LONG' else e+atr_mult*a
  fut=[]
  for k in range(entry_i,min(entry_i+h,len(rows))):
   if rows[k]['secid']!=rows[sig]['secid']: break
   fut.append(rows[k])
  if not fut: continue
  exitp=float(fut[-1]['close']); reason='TIME'; hit=None
  for k,b in enumerate(fut):
   if (float(b['low'])<=stop if s=='LONG' else float(b['high'])>=stop): exitp=stop; reason='STOP'; hit=k; break
  gross=ret_bps(s,e,exitp); hold=(hit+1) if hit is not None else len(fut)
  out.append({'family':rows[sig]['secid'][:-2],'contract':rows[sig]['secid'],'variant':variant,'side':s,'signal_time':rows[sig]['begin'],'entry_time':rows[entry_i]['begin'],'gross_bps':gross,'exit_reason':reason,'holding_bars':hold,'split':split_of(rows[sig]['begin'])})
 return out

def main():
 report={'release':'R1.4.6.1','rules':'LONG trigger only changes; SHORT is identical control','variants':{},'quality':{}}; led=[]
 chains={}
 for f in FAMILIES:
  try: chains[f]=build_chain(f,'2024-01-01','2026-09-01'); report['quality'][f]=chains[f][1]
  except Exception as e: report['quality'][f]={'status':'ERROR','error':repr(e)}
 for v in VARIANTS:
  es=[]
  for f,(rows,_) in chains.items(): es+=replay(rows,v)
  led+=es; report['variants'][v]={}
  for split in ('IS','VALIDATION','OOS'):
   ss=[e for e in es if e['split']==split]; longs=[e for e in ss if e['side']=='LONG']; shorts=[e for e in ss if e['side']=='SHORT']
   fam=[]
   for f in sorted({e['family'] for e in longs}):
    m=metrics([e for e in longs if e['family']==f],5)
    if m.get('n',0): fam.append(m.get('mean',-1)>0)
   report['variants'][v][split]={'ALL':metrics(ss,5),'LONG':metrics(longs,5),'SHORT':metrics(shorts,5),'long_positive_family_share_pct':round(100*sum(fam)/len(fam),2) if fam else 0}
  val=report['variants'][v]['VALIDATION']['LONG']; oos=report['variants'][v]['OOS']['LONG']; share=report['variants'][v]['OOS']['long_positive_family_share_pct']
  report['variants'][v]['gate']='CANDIDATE' if oos.get('n',0)>=100 and oos.get('mean',-1)>0 and (oos.get('profit_factor') or 0)>1 and val.get('mean',-1)>=0 and share>=50 else 'NO-GO'
 Path('artifacts').mkdir(exist_ok=True); Path('artifacts/r1_4_6_1_long_entry_redesign.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); Path('artifacts/r1_4_6_1_trade_ledger.json').write_text(json.dumps(led,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({v:{'validation_long':report['variants'][v]['VALIDATION']['LONG'],'oos_long':report['variants'][v]['OOS']['LONG'],'positive_family_share':report['variants'][v]['OOS']['long_positive_family_share_pct'],'gate':report['variants'][v]['gate']} for v in VARIANTS},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
