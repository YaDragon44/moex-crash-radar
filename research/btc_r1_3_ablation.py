import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from btc_crowd_oi_r1_2 import load_data, trade_backtest, event_stats

OUT=Path('research/results'); OUT.mkdir(parents=True,exist_ok=True)

def cooldown(s,bars=42):
    arr=np.zeros(len(s),dtype=bool); last=-10**9
    for i,v in enumerate(s.fillna(False).to_numpy()):
        if v and i-last>=bars: arr[i]=True; last=i
    return pd.Series(arr,index=s.index)

def run():
    _,_,_,d=load_data()
    base=(d.fgi_day<=35)&d.fgi_turn_up&d.price_confirm
    models={
      'A1_FGI_price':base,
      'A2_FGI_Trend':base&d.bull_trend,
      'A3_FGI_OIreset':base&d.oi_delev_recent&d.oi_stable,
      'A4_FGI_OIreset_Trend':base&d.oi_delev_recent&d.oi_stable&d.bull_trend,
      'A5_FGI_Trend_OInotHot':base&d.bull_trend&(d.oi_chg24<0.05),
      'A6_FGI_Trend_OIrebuild':base&d.bull_trend&(d.oi_chg24>=0)&(d.oi_chg24<0.05),
      'A7_FGI30_Trend':(d.fgi_day<=30)&d.fgi_turn_up&d.price_confirm&d.bull_trend,
    }
    rows=[]; ev=[]
    for name,raw in models.items():
        s=cooldown(raw)
        st,tr,_=trade_backtest(d,s,name)
        es,_=event_stats(d,s); es['model']=name; ev.append(es)
        if st: rows.append(st)
    stats=pd.DataFrame(rows); events=pd.DataFrame(ev)
    # crude temporal stability: rerun using signals restricted to each subperiod, while keeping indicators trained only on past data.
    stability=[]
    for label,start,end in [('2020_2022','2020-07-20','2022-12-31 23:59:59'),('2023_2026','2023-01-01','2026-03-13')]:
        mask=(d.index>=pd.Timestamp(start,tz='UTC'))&(d.index<=pd.Timestamp(end,tz='UTC'))
        for name,raw in models.items():
            s=cooldown(raw)&mask
            st,tr,_=trade_backtest(d,s,name)
            if st:
                stability.append({'period':label,'model':name,'trades':st['trades'],'ProfitFactor':st['ProfitFactor'],'WinRate':st['WinRate'],'Expectancy':st['Expectancy']})
    stab=pd.DataFrame(stability)
    stats.to_csv(OUT/'ablation_stats.csv',index=False); events.to_csv(OUT/'ablation_events.csv',index=False); stab.to_csv(OUT/'ablation_stability.csv',index=False)
    print('\n=== R1.3 ABLATION ==='); print(stats.to_string(index=False))
    print('\n=== R1.3 EVENT ==='); print(events.to_string(index=False))
    print('\n=== R1.3 STABILITY ==='); print(stab.to_string(index=False))
    print('R13_JSON='+json.dumps({'stats':json.loads(stats.to_json(orient='records')),'events':json.loads(events.to_json(orient='records')),'stability':json.loads(stab.to_json(orient='records'))}))
if __name__=='__main__': run()
