from __future__ import annotations

import json, math
from io import StringIO
from pathlib import Path
import numpy as np
import pandas as pd
import requests

BTC_FGI_URL = "https://raw.githubusercontent.com/MetalGrey/btc-fgi-daily-2020/main/datasets/btc_with_fgi_4h.csv"
BYBIT_LS_URL = "https://api.bybit.com/v5/market/account-ratio"
SYMBOL = "BTCUSDT"
PERIOD = "4h"
OOS_START = pd.Timestamp("2024-01-01")
LS_START = pd.Timestamp("2020-07-20")
FEE = 0.001


def get(url, params=None):
    r=requests.get(url,params=params,timeout=60); r.raise_for_status(); return r


def load_btc():
    d=pd.read_csv(StringIO(get(BTC_FGI_URL).text))
    d=d.rename(columns={"Fear & Greed Index":"fgi"})
    d["timestamp"]=pd.to_datetime(d["timestamp"]); d=d.sort_values("timestamp").drop_duplicates("timestamp")
    for c in ["open","high","low","close","fgi"]: d[c]=pd.to_numeric(d[c],errors="coerce")
    d["date"]=d.timestamp.dt.floor("D"); daily=d.groupby("date").fgi.first().sort_index().shift(1)
    d["fgi_safe"]=d.date.map(daily)
    d["prev3_high"]=d.high.shift(1).rolling(3).max(); d["price_confirm"]=d.close>d.prev3_high
    prev=d.close.shift(1); tr=pd.concat([d.high-d.low,(d.high-prev).abs(),(d.low-prev).abs()],axis=1).max(axis=1)
    d["atr14"]=tr.rolling(14).mean(); d["swing_low"]=d.low.shift(1).rolling(6).min()
    return d


def load_bybit_ls(end_ts: pd.Timestamp):
    rows=[]
    start=LS_START
    # 80 days = 480 four-hour observations, below Bybit max limit=500.
    while start <= end_ts:
        end=min(start+pd.Timedelta(days=80)-pd.Timedelta(milliseconds=1), end_ts)
        p={"category":"linear","symbol":SYMBOL,"period":PERIOD,"limit":500,
           "startTime":int(start.timestamp()*1000),"endTime":int(end.timestamp()*1000)}
        payload=get(BYBIT_LS_URL,p).json()
        if payload.get("retCode") != 0:
            raise RuntimeError(f"Bybit retCode={payload.get('retCode')} retMsg={payload.get('retMsg')}")
        rows.extend(payload.get("result",{}).get("list",[]))
        start=end+pd.Timedelta(milliseconds=1)
    if not rows: return pd.DataFrame()
    d=pd.DataFrame(rows)
    d["timestamp"]=pd.to_datetime(pd.to_numeric(d.timestamp),unit="ms")
    d["buy_ratio"]=pd.to_numeric(d.buyRatio,errors="coerce")
    d["sell_ratio"]=pd.to_numeric(d.sellRatio,errors="coerce")
    d["ls_ratio"]=d.buy_ratio/d.sell_ratio.replace(0,np.nan)
    d=d[["timestamp","buy_ratio","sell_ratio","ls_ratio"]].dropna().drop_duplicates("timestamp").sort_values("timestamp")
    d["gap_h"]=d.timestamp.diff().dt.total_seconds()/3600
    d["quality_ok"]=d.gap_h.isna() | (d.gap_h==4)
    d["ls_delta24"]=d.ls_ratio.pct_change(6)
    # 30-day rolling positioning distribution on 4H data.
    window=6*30
    d["ls_p10"]=d.ls_ratio.rolling(window,min_periods=window//2).quantile(.10)
    d["ls_p90"]=d.ls_ratio.rolling(window,min_periods=window//2).quantile(.90)
    return d


def sig(d,model):
    base=(d.fgi_safe<=25)&d.price_confirm.fillna(False)
    if model=="M1A": return base
    # Contrarian crowd stress: unusually short-heavy positioning or fast shift toward shorts.
    short_extreme=(d.ls_ratio<=d.ls_p10)|(d.ls_delta24<-.08)
    if model=="M2B": return base & short_extreme.fillna(False)
    raise ValueError(model)


def run(d,s,weighted=False):
    x=d.reset_index(drop=True); s=s.reset_index(drop=True)
    eq=1.; pos=0.; entry=np.nan; stop=np.nan; trades=[]; curve=[]
    for i,r in x.iterrows():
        c=float(r.close)
        if pos and i: eq*=1+pos*(c/float(x.iloc[i-1].close)-1)
        if pos and ((pd.notna(r.swing_low) and c<float(r.swing_low)) or (pd.notna(stop) and c<stop)):
            eq*=1-FEE*pos; trades.append({"ret":(c/entry-1)*pos-2*FEE*pos,"size":pos}); pos=0
        if not pos and bool(s.iloc[i]) and pd.notna(r.atr14) and pd.notna(r.swing_low):
            st=float(r.swing_low)-.5*float(r.atr14)
            if 0<c-st<=2*float(r.atr14):
                size=1.0
                if weighted:
                    if pd.notna(r.ls_p10) and r.ls_ratio<=r.ls_p10: size=1.0
                    elif pd.notna(r.ls_p90) and r.ls_ratio>=r.ls_p90: size=.5
                    else: size=.75
                eq*=1-FEE*size; pos=size; entry=c; stop=st
        curve.append(eq)
    if pos:
        eq*=1-FEE*pos; trades.append({"ret":(float(x.iloc[-1].close)/entry-1)*pos-2*FEE*pos,"size":pos}); curve[-1]=eq
    e=pd.Series(curve); peak=e.cummax(); dd=e/peak-1; rr=e.pct_change().fillna(0)
    tr=[t["ret"] for t in trades]; wins=sum(v for v in tr if v>0); losses=abs(sum(v for v in tr if v<0))
    return {"return":float(e.iloc[-1]-1),"maxdd":float(dd.min()),"sharpe":float(rr.mean()/rr.std(ddof=0)*math.sqrt(6*365)) if rr.std(ddof=0)>0 else 0.,"pf":float(wins/losses) if losses else None,"expectancy":float(np.mean(tr)) if tr else 0.,"trades":len(tr),"avg_size":float(np.mean([t['size'] for t in trades])) if trades else 0.}


def main():
    out=Path("artifacts"); out.mkdir(exist_ok=True)
    btc=load_btc(); end_ts=btc.timestamp.max(); ls=load_bybit_ls(end_ts)
    audit={"rows":len(ls),"first":str(ls.timestamp.min()) if len(ls) else None,"last":str(ls.timestamp.max()) if len(ls) else None,
           "quality_coverage_pct":float(ls.quality_ok.mean()*100) if len(ls) else 0.0}
    d=btc.merge(ls,on="timestamp",how="inner") if len(ls) else pd.DataFrame()
    if len(d): d=d[(d.timestamp>=OOS_START)&d.quality_ok].copy()
    report={"release":"R1.3.4","positioning_source":"Bybit /v5/market/account-ratio BTCUSDT 4h","audit":audit,"models":{},"verdict":"INCONCLUSIVE_INSUFFICIENT_POSITIONING_HISTORY","common_bars":len(d)}
    if len(d)>=1000:
        m1=run(d,sig(d,"M1A"))
        m2b=run(d,sig(d,"M2B"))
        m2d=run(d,sig(d,"M1A"),weighted=True)
        report["models"]={"M1A":m1,"M2B_FGI_LS_FILTER":m2b,"M2D_FGI_LS_SIZING":m2d}
        report["delta_vs_M1A"]={
            "M2B":{"return":m2b["return"]-m1["return"],"maxdd":m2b["maxdd"]-m1["maxdd"],"sharpe":m2b["sharpe"]-m1["sharpe"],"expectancy":m2b["expectancy"]-m1["expectancy"],"trades":m2b["trades"]-m1["trades"]},
            "M2D":{"return":m2d["return"]-m1["return"],"maxdd":m2d["maxdd"]-m1["maxdd"],"sharpe":m2d["sharpe"]-m1["sharpe"],"expectancy":m2d["expectancy"]-m1["expectancy"],"trades":m2d["trades"]-m1["trades"]},
        }
        report["verdict"]="POSITIONING_TEST_EXECUTED"
    (out/"btc_positioning_r1_3_4.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
