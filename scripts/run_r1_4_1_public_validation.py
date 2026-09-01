from __future__ import annotations

import argparse, json, statistics, urllib.parse, urllib.request
from datetime import date

UNIVERSE={"MX":"MXU6","SI":"SiU6","SR":"SRU6","GZ":"GZU6","BR":"BRU6","MMU":"MMU6","CRU":"CRU6","SVU":"SVU6","NG":"NGU6","RN":"RNU6","TB":"TBU6"}


def fetch(secid,start,end):
    out=[]; offset=0
    while True:
        q=urllib.parse.urlencode({"interval":60,"from":start,"till":end,"start":offset})
        u=f"https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities/{secid}/candles.json?{q}"
        with urllib.request.urlopen(u,timeout=30) as r: j=json.load(r)
        c=j.get("candles",{}); cols=[x.lower() for x in c.get("columns",[])]; data=c.get("data",[])
        if not data: break
        out += [dict(zip(cols,row)) for row in data]; offset += len(data)
        if len(data)<500: break
    return out


def ema(xs,n):
    if len(xs)<n:return None
    k=2/(n+1); e=sum(xs[:n])/n
    for x in xs[n:]: e=x*k+e*(1-k)
    return e


def rsi(xs,n=14):
    if len(xs)<n+1:return None
    g=l=0.0
    for i in range(len(xs)-n,len(xs)):
        d=xs[i]-xs[i-1]; g+=max(d,0); l+=max(-d,0)
    if l==0:return 100.0
    rs=(g/n)/(l/n); return 100-100/(1+rs)


def median(xs): return statistics.median(xs) if xs else None


def evaluate(candles,horizon=4):
    rows=[]
    for i in range(55,len(candles)-horizon):
        hist=candles[:i+1]; prev=candles[i-1]; cur=candles[i]
        try:
            closes=[float(x["close"]) for x in hist if x.get("close") is not None]
            vols=[float(x["volume"]) for x in hist if x.get("volume") is not None]
            px=float(cur["close"]); e20=ema(closes,20); e50=ema(closes,50); ep=ema(closes[:-1],20)
            if None in (e20,e50,ep): continue
            direction=1 if e20>e50 and e20>ep and px>e20 else -1 if e20<e50 and e20<ep and px<e20 else 0
            if not direction: continue
            trigger = px>float(prev["high"]) if direction==1 else px<float(prev["low"])
            if not trigger: continue
            rv=vols[-1]/median(vols[-31:-1]) if len(vols)>=31 and median(vols[-31:-1]) else None
            rr=rsi(closes); rp=rsi(closes[:-1])
            rsi_ok=(rr is not None and rp is not None and ((direction==1 and 55<=rr<=65 and rr>rp) or (direction==-1 and 35<=rr<=45 and rr<rp)))
            rvol_ok=rv is not None and rv>=1.20
            future=float(candles[i+horizon]["close"])
            signed_bps=direction*(future/px-1)*10000
            rows.append({"dir":direction,"ret_bps":signed_bps,"rsi":rsi_ok,"rvol":rvol_ok})
        except (TypeError,ValueError,KeyError,ZeroDivisionError):
            continue
    return rows


def stats(rows):
    if not rows:return {"n":0,"mean_bps":None,"median_bps":None,"hit_rate":None}
    x=[r["ret_bps"] for r in rows]
    return {"n":len(x),"mean_bps":round(sum(x)/len(x),2),"median_bps":round(statistics.median(x),2),"hit_rate":round(sum(v>0 for v in x)/len(x),4)}


def main():
    p=argparse.ArgumentParser(); p.add_argument("--start",default="2026-06-01"); p.add_argument("--end",default=str(date.today())); p.add_argument("--horizon",type=int,default=4); a=p.parse_args()
    report={"release":"R1.4.1","period":[a.start,a.end],"horizon_bars":a.horizon,"note":"Public technical validation only; OI/FUTOI excluded.","markets":[]}
    for fam,secid in UNIVERSE.items():
        try:
            candles=fetch(secid,a.start,a.end); rows=evaluate(candles,a.horizon)
            models={
                "T0_TREND_TRIGGER":stats(rows),
                "T1_PLUS_RVOL":stats([r for r in rows if r["rvol"]]),
                "T2_PLUS_RSI":stats([r for r in rows if r["rsi"]]),
                "FULL_RVOL_RSI":stats([r for r in rows if r["rvol"] and r["rsi"]]),
            }
            report["markets"].append({"family":fam,"secid":secid,"candles":len(candles),"models":models})
        except Exception as e:
            report["markets"].append({"family":fam,"secid":secid,"status":"ERROR","error":f"{type(e).__name__}: {e}"})
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
