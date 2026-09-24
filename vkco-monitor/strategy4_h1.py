from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
import requests
import monitor

STATE_FILE=Path(os.getenv("STRATEGY4_STATE_FILE","vkco-monitor/state/strategy4_h1_state.json"))
JOURNAL_FILE=Path(os.getenv("STRATEGY4_JOURNAL_JSONL","vkco-monitor/state/strategy4_h1_journal.jsonl"))

def fetch_h1(days:int=45)->list[monitor.Candle]:
    url=monitor._candles_url(monitor.TICKER,"shares",monitor.BOARD); rows=[]; cols=None; start=0
    date_from=(monitor.datetime.now(monitor.MOSCOW)-monitor.timedelta(days=days)).date().isoformat()
    while True:
        r=requests.get(url,params={"interval":60,"from":date_from,"start":start,"iss.meta":"off"},timeout=20);r.raise_for_status()
        p=r.json()["candles"];cols=cols or p["columns"];batch=p["data"];rows.extend(batch)
        if not batch or len(batch)<500:break
        start+=len(batch)
    now=monitor.datetime.now(monitor.MOSCOW);out=[]
    for row in rows:
        x=dict(zip(cols,row));c=monitor.Candle(begin=monitor._dt(x["begin"]),end=monitor._dt(x["end"]),open=float(x["open"]),close=float(x["close"]),high=float(x["high"]),low=float(x["low"]),volume=float(x.get("volume") or 0))
        if c.end<=now:out.append(c)
    if len(out)<25:raise ValueError("Need at least 25 completed H1 candles")
    return out

def evaluate(c:list[Any])->dict[str,Any]:
    lv=monitor.adaptive_levels(c);a,b,z=c[-3],c[-2],c[-1];av=lv["avg_volume"];rb=b.volume/av;rz=z.volume/av
    signal=None
    if a.close<=lv["resistance"] and b.close>lv["resistance"] and z.close>lv["resistance"] and rb>=1.20:
        stop=lv["resistance"]-max(lv["avg_range"]*.60,.30);risk=max(z.close-stop,.01);signal={"kind":"ADAPTIVE_BREAKOUT","setup":"Adaptive Breakout + Hold","entry":z.close,"stop":round(stop,2),"tp1":round(z.close+1.5*risk,2),"tp2":round(z.close+2.5*risk,2),"tp3":round(z.close+4*risk,2),"rvol":round(max(rb,rz),2)}
    elif b.low<lv["support"] and b.close>lv["support"] and z.low>=lv["support"] and z.close>=b.close and rb>=1.30:
        stop=b.low-max(lv["avg_range"]*.25,.20);risk=max(z.close-stop,.01);signal={"kind":"ADAPTIVE_SPRING","setup":"Adaptive Wyckoff Spring","entry":z.close,"stop":round(stop,2),"tp1":round(max(lv["resistance"],z.close+1.5*risk),2),"tp2":round(z.close+2.5*risk,2),"tp3":round(z.close+4*risk,2),"rvol":round(max(rb,rz),2)}
    return {"strategy":"S4_ADAPTIVE_H1","timeframe":"H1","mode":"SHADOW","candle":z.end.isoformat(),"price":z.close,"support":round(lv["support"],2),"resistance":round(lv["resistance"],2),"avg_range":round(lv["avg_range"],4),"decision":"READY" if signal else "WAIT","reason":"TRIGGER_CONFIRMED" if signal else "NO_TRIGGER","signal":signal}

def _load():
    try:return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except:return {}
def journal():
    if not JOURNAL_FILE.exists():return []
    out=[]
    for x in JOURNAL_FILE.read_text().splitlines():
        try:out.append(json.loads(x))
        except:pass
    return out
def run_shadow(c:list[Any])->dict[str,Any]:
    s=evaluate(c);state=_load();changed=False
    if s["decision"]=="READY":
        eid=f"S4:{s['signal']['kind']}:{s['candle']}"
        if state.get("last_event_id")!=eid:
            JOURNAL_FILE.parent.mkdir(parents=True,exist_ok=True)
            rec={**s,"event_id":eid}; 
            with JOURNAL_FILE.open("a",encoding="utf-8") as f:f.write(json.dumps(rec,ensure_ascii=False)+"\n")
            STATE_FILE.write_text(json.dumps({"last_event_id":eid},ensure_ascii=False),encoding="utf-8");changed=True
    return {**s,"journal_appended":changed}

def public_snapshot(c:list[Any])->dict[str,Any]:
    s=evaluate(c);rows=journal()
    return {**s,"journal":rows[-20:],"signals":len(rows)}
