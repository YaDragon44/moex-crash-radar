from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
import requests
import monitor
import position_manager
import trade_journal
import trade_plan

STATE_FILE=Path(os.getenv("STRATEGY4_STATE_FILE","vkco-monitor/state/strategy4_h1_state.json"))
JOURNAL_FILE=Path(os.getenv("STRATEGY4_JOURNAL_JSONL","vkco-monitor/state/strategy4_h1_journal.jsonl"))

def fetch_h1(days:int=45,secid:str=monitor.TICKER,market:str="shares",board:str|None=monitor.BOARD)->list[monitor.Candle]:
    url=monitor._candles_url(secid,market,board); rows=[]; cols=None; start=0
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
        stop=lv["resistance"]-max(lv["avg_range"]*.60,.30);risk=max(z.close-stop,.01);signal={"kind":"ADAPTIVE_BREAKOUT","setup":"Adaptive Breakout + Hold","entry":z.close,"price":z.close,"time":z.end.isoformat(),"signal_id":f"S4:H1:ADAPTIVE_BREAKOUT:{z.end.isoformat()}","score":None,"stop":round(stop,2),"tp1":round(z.close+1.5*risk,2),"tp2":round(z.close+2.5*risk,2),"tp3":round(z.close+4*risk,2),"rvol":round(max(rb,rz),2)}
    elif b.low<lv["support"] and b.close>lv["support"] and z.low>=lv["support"] and z.close>=b.close and rb>=1.30:
        stop=b.low-max(lv["avg_range"]*.25,.20);risk=max(z.close-stop,.01);signal={"kind":"ADAPTIVE_SPRING","setup":"Adaptive Wyckoff Spring","entry":z.close,"price":z.close,"time":z.end.isoformat(),"signal_id":f"S4:H1:ADAPTIVE_SPRING:{z.end.isoformat()}","score":None,"stop":round(stop,2),"tp1":round(max(lv["resistance"],z.close+1.5*risk),2),"tp2":round(z.close+2.5*risk,2),"tp3":round(z.close+4*risk,2),"rvol":round(max(rb,rz),2)}
    return {"strategy":"S4_ADAPTIVE_H1","timeframe":"H1","mode":"SHADOW","candle":z.end.isoformat(),"price":z.close,"support":round(lv["support"],2),"resistance":round(lv["resistance"],2),"avg_range":round(lv["avg_range"],4),"decision":"READY" if signal else "WAIT","reason":"TRIGGER_CONFIRMED" if signal else "NO_TRIGGER","signal":signal}

def h1_market_filter(c:list[Any])->dict[str,Any]:
    if len(c)<21: raise ValueError("Need at least 21 completed IMOEX H1 candles")
    latest=c[-1];sma20=sum(float(x.close) for x in c[-20:])/20.0
    prev=float(c[-2].close);ret=(float(latest.close)/prev-1.0)*100 if prev else 0.0
    ok=float(latest.close)>=sma20*.995 and ret>=-.70
    return {"ok":ok,"close":latest.close,"sma20":round(sma20,4),"return_1h_pct":round(ret,3),"time":latest.end.isoformat()}

def decision_snapshot(c:list[Any])->dict[str,Any]:
    s=evaluate(c)
    if s["decision"]!="READY": return {**s,"imoex":None,"event_risk":None}
    imo=h1_market_filter(fetch_h1(days=45,secid="IMOEX",market="index",board=None))
    if not imo["ok"]: return {**s,"decision":"WAIT","reason":"MARKET_FILTER","imoex":imo,"event_risk":None}
    try: ev=monitor.fetch_event_risk(window_days=3)
    except Exception as exc: return {**s,"decision":"WAIT","reason":"EVENT_DATA_UNAVAILABLE","imoex":imo,"event_risk":{"ok":False,"error":type(exc).__name__}}
    evp={"ok":ev.get("ok",False),"window_days":ev.get("window_days"),"source":ev.get("source"),"items":ev.get("items",[])[:3]}
    if not evp["ok"]: return {**s,"decision":"WAIT","reason":"EVENT_RISK","imoex":imo,"event_risk":evp}
    return {**s,"imoex":imo,"event_risk":evp}

def _load():
    return position_manager.load_state_file(STATE_FILE)

def journal():
    return trade_journal.load_records(JOURNAL_FILE)

def _manage_active(c:list[Any], state:dict[str,Any])->tuple[dict[str,Any],str|None]:
    p=state.get("position")
    if not p or not position_manager.has_active_position(state):
        return state,None
    lv=monitor.adaptive_levels(c)
    updated,event=position_manager.manage_position(p,c[-1],lv["avg_range"])
    state={**state,"position":updated}
    if event in {"CLOSED_PROFIT","CLOSED_STOP"}:
        trade_journal.append_record_once(JOURNAL_FILE,updated)
    position_manager.save_state_file(STATE_FILE,state)
    return state,event

def run_shadow(c:list[Any])->dict[str,Any]:
    state=_load()
    if position_manager.has_active_position(state):
        state,event=_manage_active(c,state)
        snap=evaluate(c)
        return {**snap,"decision":"HOLD" if position_manager.has_active_position(state) else "WAIT",
                "reason":event or "MODEL_POSITION_ACTIVE","position":state.get("position"),
                "journal_appended":event in {"CLOSED_PROFIT","CLOSED_STOP"}}
    s=decision_snapshot(c);changed=False
    if s["decision"]=="READY":
        sig=s["signal"];plan=trade_plan.build_trade_plan(sig)
        pos=position_manager.open_position(sig,plan)
        state={"position":pos,"last_signal_id":sig["signal_id"]}
        position_manager.save_state_file(STATE_FILE,state);changed=True
    return {**s,"position":state.get("position"),"journal_appended":changed}

def public_snapshot(c:list[Any])->dict[str,Any]:
    s=decision_snapshot(c);state=_load();rows=journal();st=trade_journal.stats(rows)
    if position_manager.has_active_position(state):
        s={**s,"decision":"HOLD","reason":"MODEL_POSITION_ACTIVE"}
    return {**s,"position":state.get("position"),"journal":rows[-20:],"signals":len(rows),
            "closed_trades":st["trades"],"wins":st["wins"],"losses":st["losses"],
            "win_rate":st["win_rate"],"avg_r":st["avg_r"],"profit_factor":st["profit_factor"],
            "expectancy_r":st["expectancy_r"]}
