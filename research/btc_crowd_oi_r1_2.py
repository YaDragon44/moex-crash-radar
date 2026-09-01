import json, math, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

BTC_FGI_URL = 'https://raw.githubusercontent.com/MetalGrey/btc-fgi-daily-2020/main/datasets/btc_with_fgi_4h.csv'
OI_URL = 'https://gist.githubusercontent.com/vadim-isakov/bb200237e444cf6656535c22840f45fd/raw/btcusdt_open_interest_4h.csv'
FUNDING_URL = 'https://gist.githubusercontent.com/vadim-isakov/6ca19296c32dc3beabc5016dfec52e38/raw/btcusdt_funding_rate.csv'
OUT = Path('research/results')
OUT.mkdir(parents=True, exist_ok=True)

def rsi(s, n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad=dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs=au/ad.replace(0,np.nan)
    return 100-(100/(1+rs))

def atr(df,n=14):
    pc=df.close.shift(1)
    tr=pd.concat([(df.high-df.low).abs(),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def load_data():
    print('DOWNLOAD', BTC_FGI_URL)
    p=pd.read_csv(BTC_FGI_URL)
    p['timestamp']=pd.to_datetime(p['timestamp'],utc=True)
    p=p.sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')
    p=p.rename(columns={'Fear & Greed Index':'fgi','Fear & Greed Classification':'fgi_class'})
    for c in ['open','close','high','low','fgi']: p[c]=pd.to_numeric(p[c],errors='coerce')

    print('DOWNLOAD', OI_URL)
    oi=pd.read_csv(OI_URL)
    oi['timestamp']=pd.to_datetime(pd.to_numeric(oi['timestamp']),unit='ms',utc=True)
    oi['openInterest']=pd.to_numeric(oi['openInterest'],errors='coerce')
    oi=oi.sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp').rename(columns={'openInterest':'oi'})

    print('DOWNLOAD', FUNDING_URL)
    fu=pd.read_csv(FUNDING_URL)
    fu['timestamp']=pd.to_datetime(pd.to_numeric(fu.iloc[:,0]),unit='ms',utc=True)
    fu['funding']=pd.to_numeric(fu.iloc[:,1],errors='coerce')
    fu=fu[['timestamp','funding']].sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')

    # exact 4h merge for OI; asof funding because it settles every ~8h
    d=p.join(oi,how='inner')
    d=pd.merge_asof(d.reset_index().sort_values('timestamp'),fu.reset_index().sort_values('timestamp'),on='timestamp',direction='backward',tolerance=pd.Timedelta('12h')).set_index('timestamp')
    d=d.sort_index()

    d['ret4h']=d.close.pct_change()
    d['oi_chg24']=d.oi.pct_change(6)
    d['oi_dd7']=d.oi/d.oi.rolling(42,min_periods=12).max()-1
    d['rsi14']=rsi(d.close,14)
    d['atr14']=atr(d,14)
    d['ema20_4h']=d.close.ewm(span=20,adjust=False).mean()

    # daily EMA200 and slope, calculated only from completed UTC days then shifted 1 day to avoid intraday look-ahead
    daily=d.close.resample('1D').last().dropna().to_frame('dclose')
    daily['ema200']=daily.dclose.ewm(span=200,adjust=False,min_periods=200).mean()
    daily['ema200_prev10']=daily.ema200.shift(10)
    daily[['ema200','ema200_prev10']]=daily[['ema200','ema200_prev10']].shift(1)
    d=pd.merge_asof(d.reset_index(),daily[['ema200','ema200_prev10']].reset_index().rename(columns={'index':'timestamp'}),on='timestamp',direction='backward').set_index('timestamp')
    d['bull_trend']=(d.close>d.ema200)&(d.ema200>d.ema200_prev10)

    # rolling funding percentile using only prior observations; 180d ~ 540 settlements
    fr=fu.copy()
    fr['fund_pct']=fr.funding.shift(1).rolling(540,min_periods=90).rank(pct=True)
    d=pd.merge_asof(d.reset_index(),fr[['fund_pct']].reset_index(),on='timestamp',direction='backward',tolerance=pd.Timedelta('12h')).set_index('timestamp')

    # Daily FGI transition without using future values: at 4h bars, compare currently known daily fgi vs prior distinct day values.
    fday=d.fgi.resample('1D').last().dropna()
    fdf=pd.DataFrame({'fgi_day':fday,'fgi_prev':fday.shift(1),'fgi_prev3min':fday.shift(1).rolling(3,min_periods=1).min()})
    d=pd.merge_asof(d.reset_index(),fdf.reset_index().rename(columns={'index':'timestamp'}),on='timestamp',direction='backward').set_index('timestamp')
    d['fgi_turn_up']=(d.fgi_day>d.fgi_prev)&(d.fgi_prev<=d.fgi_prev3min+1e-9)

    # Price confirmation: close above max of previous 3 completed 4h closes
    d['price_confirm']=d.close>d.close.shift(1).rolling(3).max()
    d['rsi_cross35']=(d.rsi14>35)&(d.rsi14.shift(1)<=35)
    d['oi_delev_recent']=((d.oi_dd7<=-0.05)|(d.oi_chg24<=-0.05)).rolling(42,min_periods=1).max().astype(bool)
    d['oi_stable']=d.oi_chg24>-0.03
    d['fund_washed']= (d.fund_pct<=0.20).rolling(42,min_periods=1).max().astype(bool)
    return p,oi,fu,d

def build_signals(d):
    base=(d.fgi_day<=35)&d.fgi_turn_up&d.price_confirm
    m={}
    m['M1_FGI']=base
    m['M2_FGI_OI']=base&d.oi_delev_recent&d.oi_stable
    m['M3_plus_RSI']=m['M2_FGI_OI']&d.rsi_cross35
    m['M4_plus_Trend']=m['M2_FGI_OI']&d.bull_trend
    m['M5_plus_Funding']=m['M2_FGI_OI']&d.fund_washed
    m['M6_Full']=m['M2_FGI_OI']&d.rsi_cross35&d.bull_trend&d.fund_washed
    # de-duplicate event signals: require 7d cooldown after a signal
    out={}
    for k,s in m.items():
        arr=np.zeros(len(d),dtype=bool); last=-10**9
        for i,v in enumerate(s.fillna(False).to_numpy()):
            if v and i-last>=42:
                arr[i]=True; last=i
        out[k]=pd.Series(arr,index=d.index)
    return out

def event_stats(d,s):
    idx=np.flatnonzero(s.to_numpy())
    rows=[]
    for i in idx:
        r={'timestamp':d.index[i],'entry':d.close.iloc[i]}
        for bars,days in [(42,7),(84,14),(180,30)]:
            if i+bars<len(d):
                r[f'ret_{days}d']=d.close.iloc[i+bars]/d.close.iloc[i]-1
                window=d.close.iloc[i:i+bars+1]
                r[f'mae_{days}d']=window.min()/d.close.iloc[i]-1
                r[f'mfe_{days}d']=window.max()/d.close.iloc[i]-1
        rows.append(r)
    x=pd.DataFrame(rows)
    res={'events':len(x)}
    for days in [7,14,30]:
        c=f'ret_{days}d'
        if c in x and x[c].notna().any():
            z=x[c].dropna(); res[f'avg_{days}d']=float(z.mean()); res[f'median_{days}d']=float(z.median()); res[f'hit_{days}d']=float((z>0).mean())
            res[f'n_{days}d']=int(len(z))
    return res,x

def trade_backtest(d,s,name,fee=0.001,max_hold_bars=180):
    # LONG-only, all-in research strategy. Enter at next bar open after signal.
    # Exit on: FGI>=75 and turns down, 4h close below EMA20 after 2R advance, hard -10%, or max 30d.
    trades=[]; i=0; sig=s.to_numpy()
    while i<len(d)-2:
        if not sig[i]: i+=1; continue
        e=i+1; ep=float(d.open.iloc[e])*(1+fee)
        if not np.isfinite(ep): i+=1; continue
        atr0=float(d.atr14.iloc[i]) if np.isfinite(d.atr14.iloc[i]) else ep*0.03
        initial_r=max(2*atr0,ep*0.03)
        stop=ep*0.90
        peak=ep; exit_i=min(e+max_hold_bars,len(d)-1); reason='MAX30D'
        for j in range(e+1,min(e+max_hold_bars+1,len(d))):
            lo=float(d.low.iloc[j]); hi=float(d.high.iloc[j]); cl=float(d.close.iloc[j]); peak=max(peak,hi)
            if lo<=stop:
                xp=stop*(1-fee); exit_i=j; reason='STOP10'; break
            fgi_exit=(d.fgi_day.iloc[j]>=75 and d.fgi_day.iloc[j]<d.fgi_prev.iloc[j])
            trail=(peak>=ep+2*initial_r and cl<d.ema20_4h.iloc[j])
            if fgi_exit or trail:
                xp=cl*(1-fee); exit_i=j; reason='FGI_EXIT' if fgi_exit else 'TRAIL'; break
        else:
            xp=float(d.close.iloc[exit_i])*(1-fee)
        ret=xp/ep-1
        trades.append({'model':name,'signal_time':d.index[i],'entry_time':d.index[e],'exit_time':d.index[exit_i],'entry':ep,'exit':xp,'return':ret,'reason':reason,'bars':exit_i-e})
        i=exit_i+1
    t=pd.DataFrame(trades)
    if t.empty: return {},t,None
    # Sequential all-in equity for trade-only strategy; cash is flat between trades.
    eq=(1+t['return']).cumprod()
    dd=eq/eq.cummax()-1
    years=(d.index[-1]-d.index[0]).total_seconds()/(365.25*86400)
    final=float(eq.iloc[-1]); cagr=final**(1/years)-1 if years>0 else np.nan
    wins=t.loc[t['return']>0,'return']; losses=t.loc[t['return']<0,'return']
    pf=float(wins.sum()/(-losses.sum())) if len(losses) and -losses.sum()>0 else np.inf
    win=float((t['return']>0).mean())
    exp=float(t['return'].mean())
    # Sharpe on per-trade returns annualized by trades/year (research approximation)
    tpy=len(t)/years if years>0 else np.nan
    sh=float(t['return'].mean()/t['return'].std(ddof=1)*math.sqrt(tpy)) if len(t)>1 and t['return'].std(ddof=1)>0 else np.nan
    maxdd=float(dd.min())
    stats={'model':name,'trades':int(len(t)),'total_return':final-1,'CAGR':cagr,'MaxDD':maxdd,'Sharpe_trade':sh,'ProfitFactor':pf,'WinRate':win,'Expectancy':exp,'ReturnMaxDD':(cagr/abs(maxdd) if maxdd<0 else np.nan),'avg_hold_days':float(t.bars.mean()*4/24)}
    return stats,t,eq

def buyhold(d,fee=0.001):
    start=max(d.index.min(),pd.Timestamp('2020-08-01',tz='UTC')); z=d.loc[start:].copy()
    ep=float(z.open.iloc[0])*(1+fee); xp=float(z.close.iloc[-1])*(1-fee); total=xp/ep-1
    eq=z.close/z.close.iloc[0]
    dd=eq/eq.cummax()-1
    years=(z.index[-1]-z.index[0]).total_seconds()/(365.25*86400)
    cagr=(1+total)**(1/years)-1
    r=z.close.pct_change().dropna(); sharpe=float(r.mean()/r.std()*math.sqrt(6*365.25))
    maxdd=float(dd.min())
    return {'model':'M0_BuyHold','trades':1,'total_return':total,'CAGR':cagr,'MaxDD':maxdd,'Sharpe_trade':sharpe,'ProfitFactor':np.nan,'WinRate':np.nan,'Expectancy':total,'ReturnMaxDD':cagr/abs(maxdd),'avg_hold_days':years*365.25}

def sensitivity(d):
    rows=[]
    for fthr in [25,30,35,40]:
      for oithr in [-0.03,-0.05,-0.075,-0.10]:
        base=(d.fgi_day<=fthr)&d.fgi_turn_up&d.price_confirm
        delev=((d.oi_dd7<=oithr)|(d.oi_chg24<=oithr)).rolling(42,min_periods=1).max().astype(bool)
        s=base&delev&d.oi_stable
        arr=np.zeros(len(d),dtype=bool); last=-10**9
        for i,v in enumerate(s.fillna(False).to_numpy()):
            if v and i-last>=42: arr[i]=True; last=i
        st,_,_=trade_backtest(d,pd.Series(arr,index=d.index),f'F{fthr}_OI{oithr}')
        if st: rows.append({'fear_thr':fthr,'oi_thr':oithr,**{k:st[k] for k in ['trades','CAGR','MaxDD','ProfitFactor','WinRate','Expectancy','ReturnMaxDD']}})
    return pd.DataFrame(rows)

def main():
    p,oi,fu,d=load_data()
    first=max(p.index.min(),oi.index.min(),fu.index.min())
    last=min(p.index.max(),oi.index.max(),fu.index.max())
    q={
      'price_fgi_start':str(p.index.min()),'price_fgi_end':str(p.index.max()),'price_fgi_rows':len(p),
      'oi_start':str(oi.index.min()),'oi_end':str(oi.index.max()),'oi_rows':len(oi),
      'funding_start':str(fu.index.min()),'funding_end':str(fu.index.max()),'funding_rows':len(fu),
      'merged_start':str(d.index.min()),'merged_end':str(d.index.max()),'merged_rows':len(d),
      'merged_missing_funding_pct':float(d.funding.isna().mean()),'merged_missing_ema200_pct':float(d.ema200.isna().mean()),
      'duplicate_timestamps':int(d.index.duplicated().sum()),
    }
    signals=build_signals(d)
    all_stats=[buyhold(d)]; evrows=[]; all_trades=[]
    for name,s in signals.items():
        ev,ex=event_stats(d,s); ev['model']=name; evrows.append(ev)
        st,tr,eq=trade_backtest(d,s,name)
        if st: all_stats.append(st)
        if not tr.empty: all_trades.append(tr)
    stats=pd.DataFrame(all_stats)
    events=pd.DataFrame(evrows)
    trades=pd.concat(all_trades,ignore_index=True) if all_trades else pd.DataFrame()
    sens=sensitivity(d)
    stats.to_csv(OUT/'model_stats.csv',index=False)
    events.to_csv(OUT/'event_stats.csv',index=False)
    trades.to_csv(OUT/'trades.csv',index=False)
    sens.to_csv(OUT/'sensitivity.csv',index=False)
    (OUT/'quality.json').write_text(json.dumps(q,indent=2),encoding='utf-8')
    print('\n=== QUALITY ==='); print(json.dumps(q,indent=2))
    print('\n=== MODEL STATS ==='); print(stats.to_string(index=False))
    print('\n=== EVENT STATS ==='); print(events.to_string(index=False))
    print('\n=== SENSITIVITY ==='); print(sens.to_string(index=False))
    print('\nRESULT_JSON='+json.dumps({'quality':q,'models':json.loads(stats.to_json(orient='records')),'events':json.loads(events.to_json(orient='records'))}))

if __name__=='__main__': main()
