from __future__ import annotations
import json, math
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain, atrs, ema, side, ret_bps, split_of, metrics
FAMILIES=['MX','SI','SBER','GD','MMU','CRU','SVU','NG','GAZP','ROSN','T']; VARIANTS=('P0_BREAKOUT','P1_TOUCH_RECLAIM','P2_CLOSE_RECLAIM')
def ema_series(rows,n):
 out=[]; c=[]
 for r in rows:c.append(float(r['close']));out.append(ema(c,n))
 return out
def trade(rows,i,s,a,h=8):
 if i+1>=len(rows) or rows[i+1]['secid']!=rows[i]['secid'] or not math.isfinite(a) or a<=0:return None
 e=float(rows[i+1]['open']);stop=e-1.5*a if s=='LONG' else e+1.5*a; fut=[]
 for j in range(i+1,min(i+1+h,len(rows))):
  if rows[j]['secid']!=rows[i]['secid']:break
  fut.append(rows[j])
 if not fut:return None
 exitp=float(fut[-1]['close']);reason='TIME';hit=None
 for k,b in enumerate(fut):
  if (float(b['low'])<=stop if s=='LONG' else float(b['high'])>=stop):exitp=stop;reason='STOP';hit=k;break
 gross=ret_bps(s,e,exitp);hold=(hit+1) if hit is not None else len(fut)
 return {'family':rows[i]['secid'][:-2],'contract':rows[i]['secid'],'side':s,'signal_time':rows[i]['begin'],'entry_time':rows[i+1]['begin'],'gross_bps':gross,'exit_reason':reason,'holding_bars':hold,'split':split_of(rows[i]['begin'])}
def replay(rows,v):
 aa=atrs(rows);e20=ema_series(rows,20);e50=ema_series(rows,50);out=[]
 for i in range(52,len(rows)-1):
  s=side(rows,i)
  signal=False
  if s=='SHORT':
   signal=float(rows[i]['close'])<float(rows[i-1]['low'])
  elif s=='LONG':
   if v=='P0_BREAKOUT':signal=float(rows[i]['close'])>float(rows[i-1]['high'])
   elif v=='P1_TOUCH_RECLAIM':
    signal=(float(rows[i-1]['close'])>e20[i-1] and float(rows[i]['low'])<=e20[i] and float(rows[i]['close'])>e20[i])
   elif v=='P2_CLOSE_RECLAIM':
    # prior bar closes below/at EMA20 after a bar above; current bar restores valid rising LONG trend
    signal=(float(rows[i-2]['close'])>e20[i-2] and float(rows[i-1]['close'])<=e20[i-1] and float(rows[i]['close'])>e20[i] and e20[i]>e50[i] and e20[i]>e20[i-1])
  if not signal:continue
  t=trade(rows,i,s,aa[i]);
  if t:t['variant']=v;out.append(t)
 return out
def main():
 report={'release':'R1.4.6.2','variants':{},'quality':{}};chains={};ledger=[]
 for f in FAMILIES:
  try:chains[f]=build_chain(f,'2024-01-01','2026-09-01');report['quality'][f]=chains[f][1]
  except Exception as x:report['quality'][f]={'status':'ERROR','error':repr(x)}
 for v in VARIANTS:
  es=[]
  for f,(rows,_) in chains.items():es+=replay(rows,v)
  ledger+=es;report['variants'][v]={}
  for sp in ('IS','VALIDATION','OOS'):
   ss=[e for e in es if e['split']==sp];lo=[e for e in ss if e['side']=='LONG'];sh=[e for e in ss if e['side']=='SHORT'];fam=[]
   for f in sorted({e['family'] for e in lo}):
    m=metrics([e for e in lo if e['family']==f],5)
    if m.get('n',0):fam.append(m.get('mean',-1)>0)
   report['variants'][v][sp]={'ALL':metrics(ss,5),'LONG':metrics(lo,5),'SHORT':metrics(sh,5),'long_positive_family_share_pct':round(100*sum(fam)/len(fam),2) if fam else 0}
  val=report['variants'][v]['VALIDATION']['LONG'];o=report['variants'][v]['OOS']['LONG'];share=report['variants'][v]['OOS']['long_positive_family_share_pct']
  report['variants'][v]['gate']='CANDIDATE' if o.get('n',0)>=100 and o.get('mean',-1)>0 and (o.get('profit_factor') or 0)>1 and val.get('mean',-1)>=0 and share>=50 else 'NO-GO'
 Path('artifacts').mkdir(exist_ok=True);Path('artifacts/r1_4_6_2_long_pullback_reclaim.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');Path('artifacts/r1_4_6_2_trade_ledger.json').write_text(json.dumps(ledger,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({v:{'validation':report['variants'][v]['VALIDATION']['LONG'],'oos':report['variants'][v]['OOS']['LONG'],'breadth':report['variants'][v]['OOS']['long_positive_family_share_pct'],'gate':report['variants'][v]['gate']} for v in VARIANTS},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
