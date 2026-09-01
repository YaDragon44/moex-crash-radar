from __future__ import annotations

import json, math
from io import StringIO
from pathlib import Path
import numpy as np
import pandas as pd
import requests

BTC_FGI_URL = "https://raw.githubusercontent.com/MetalGrey/btc-fgi-daily-2020/main/datasets/btc_with_fgi_4h.csv"
BINANCE_LS_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
SYMBOL = "BTCUSDT"
PERIOD = "4h"
OOS_START = pd.Timestamp("2024-01-01")
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


def load_binance_ls():
    # Binance public REST exposes only recent positioning history. We audit it explicitly;
    # insufficient history must produce INCONCLUSIVE, never a false strategy verdict.
    rows=[]; end=None
    for _ in range(20):
        p={"symbol":SYMBOL,"period":PERIOD,"limit":500}
        if end is not None: p["endTime"]=end
        x=get(BINANCE_LS_URL,p).json()
        if not x: break
        rows.extend(x); first=min(int(v["timestamp"]) for v in x); end=first-1
        if len(x)<500: break
    if not rows: return pd.DataFrame()
    d=pd.DataFrame(rows); d["timestamp"]=pd.to_datetime(pd.to_numeric(d.timestamp),unit="ms")
    d["ls_ratio"]=pd.to_numeric(d.longShortRatio,errors="coerce")
    d=d[["timestamp","ls_ratio"]].dropna().drop_duplicates("timestamp").sort_values("timestamp")
    d["ls_delta24"]=d.ls_ratio.pct_change(6)
    d["ls_p10"]=d.ls_ratio.rolling(180,min_periods=90).quantile(.10)
    d["ls_p90"]=d.ls_ratio.rolling(180,min_periods=90).quantile(.90)
    return d


def sig(d,model):
    base=(d.fgi_safe<=25)&d.price_confirm.fillna(False)
    if model=="M1A": return base
    short_extreme=(d.ls_ratio<=d.ls_p10)|(d.ls_delta24<-.08)
    if model=="M2B": return base & short_extreme.fillna(False)
    raise ValueError(model)


def run(d,s,weighted=False):
    eq=1.; pos=0.; entry=np.nan; stop=np.nan; trades=[]; curve=[]
    for i,r in d.reset_index(drop=True).iterrows():
        c=float(r.close)
        if pos and i: eq*=c/float(d.reset_index(drop=True).iloc[i-1].close)
        if pos and ((pd.notna(r.swing_low) and c<float(r.swing_low)) or (pd.notna(stop) and c<stop)):
            eq*=1-FEE; trades.append(c/entry-1-2*FEE); pos=0
        if not pos and bool(s.reset_index(drop=True).iloc[i]) and pd.notna(r.atr14) and pd.notna(r.swing_low):
            st=float(r.swing_low)-.5*float(r.atr14)
            if 0<c-st<=2*float(r.atr14):
                # M2D: positioning changes size, never blocks the trade.
                size=1.0
                if weighted:
                    if pd.notna(r.ls_p10) and r.ls_ratio<=r.ls_p10: size=1.0
                    elif pd.notna(r.ls_p90) and r.ls_ratio>=r.ls_p90: size=.5
                    else: size=.75
                eq*=1-FEE*size; pos=size; entry=c; stop=st
        curve.append(eq)
    if pos: eq*=1-FEE*pos; trades.append(float(d.iloc[-1].close)/entry-1-2*FEE); curve[-1]=eq
    e=pd.Series(curve); peak=e.cummax(); dd=e/peak-1; rr=e.pct_change().fillna(0)
    wins=sum(x for x in trades if x>0); losses=abs(sum(x for x in trades if x<0))
    return {"return":float(e.iloc[-1]-1),"maxdd":float(dd.min()),"sharpe":float(rr.mean()/rr.std(ddof=0)*math.sqrt(6*365)) if rr.std(ddof=0)>0 else 0.,"pf":float(wins/losses) if losses else None,"expectancy":float(np.mean(trades)) if trades else 0.,"trades":len(trades)}


def main():
    out=Path("artifacts"); out.mkdir(exist_ok=True)
    btc=load_btc(); ls=load_binance_ls()
    audit={"rows":len(ls),"first":str(ls.timestamp.min()) if len(ls) else None,"last":str(ls.timestamp.max()) if len(ls) else None}
    if len(ls):
        d=btc.merge(ls,on="timestamp",how="inner"); d=d[d.timestamp>=OOS_START].copy()
    else: d=pd.DataFrame()
    report={"release":"R1.3.4","positioning_source":"Binance globalLongShortAccountRatio","audit":audit,"models":{},"verdict":"INCONCLUSIVE_INSUFFICIENT_POSITIONING_HISTORY"}
    if len(d)>=1000:
        report["models"]["M1A"]=run(d,sig(d,"M1A"))
        report["models"]["M2B_FGI_LS_FILTER"]=run(d,sig(d,"M2B"))
        report["models"]["M2D_FGI_LS_SIZING"]=run(d,sig(d,"M1A"),weighted=True)
        report["verdict"]="POSITIONING_TEST_EXECUTED"
    report["common_bars"]=len(d)
    (out/"btc_positioning_r1_3_4.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
