from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
from strategy2_ema import ema

STATE_FILE=Path(os.getenv("STRATEGY3_STATE_FILE","vkco-monitor/state/strategy3_value_rsi_state.json"))
JOURNAL_FILE=Path(os.getenv("STRATEGY3_JOURNAL_JSONL","vkco-monitor/state/strategy3_value_rsi_journal.jsonl"))

def rsi(values:list[float],period:int=14)->float:
    if len(values)<period+1: raise ValueError("Need RSI history")
    gains=[]; losses=[]
    for a,b in zip(values[-period-1:-1],values[-period:]):
        d=b-a; gains.append(max(d,0)); losses.append(max(-d,0))
    ag=sum(gains)/period; al=sum(losses)/period
    if al==0: return 100.0
    return 100-(100/(1+ag/al))

def evaluate(candles:list[Any],consensus:dict[str,Any])->dict[str,Any]:
    if len(candles)<201: raise ValueError("Need 201 completed M10 candles")
    if consensus.get("status")!="OK" or not consensus.get("consensus_target"): raise ValueError("FAIR_VALUE_UNAVAILABLE")
    closes=[float(c.close) for c in candles]; price=closes[-1]
    rv=round(rsi(closes),2); e200=round(ema(closes,200)[-1],4)
    fair=float(consensus["consensus_target"]); gap=(fair/price-1)*100 if price else None
    trend="ABOVE_EMA200" if price>=e200 else "BELOW_EMA200"
    if rv<30 and gap>=20 and trend=="ABOVE_EMA200": decision="BUY"
    elif rv<30 and gap>=20: decision="WATCH"
    elif rv>70 and gap<=10: decision="SELL"
    elif rv>70 and gap>20: decision="HOLD"
    elif gap>=20: decision="WATCH"
    else: decision="WAIT"
    return {"strategy":"S3_VALUE_RSI_EMA200_M10","candle":candles[-1].end.isoformat(),"price":price,"rsi14":rv,"fair_value":fair,
      "fair_low":consensus.get("target_low"),"fair_high":consensus.get("target_high"),"valuation_gap_pct":round(gap,2),
      "ema200":e200,"trend":trend,"decision":decision}

def _load(path=STATE_FILE):
    try:return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:return {}
def _save(x,path=STATE_FILE): path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
def journal(path=JOURNAL_FILE):
    if not path.exists():return []
    out=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        try:out.append(json.loads(line))
        except Exception:pass
    return out
def _append(x,path=JOURNAL_FILE):
    if any(r.get("event_id")==x["event_id"] for r in journal(path)):return False
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(x,ensure_ascii=False)+"\n")
    return True

def run_shadow(candles:list[Any],consensus:dict[str,Any])->dict[str,Any]:
    snap=evaluate(candles,consensus); state=_load(); decision=snap["decision"]; changed=False
    event_id=f"{snap['strategy']}:{decision}:{snap['candle']}"
    if decision=="BUY" and not state.get("position"):
        changed=_append({**snap,"event_id":event_id,"action":"OPEN_LONG"})
        if changed: state={"position":{"entry":snap["price"],"opened_at":snap["candle"]},"last_event_id":event_id};_save(state)
    elif decision=="SELL" and state.get("position"):
        pos=state["position"];entry=float(pos["entry"]);pct=(snap["price"]/entry-1)*100
        changed=_append({**snap,"event_id":event_id,"action":"CLOSE_LONG","entry":entry,"opened_at":pos.get("opened_at"),"exit":snap["price"],"result_pct":round(pct,3)})
        if changed: state={"position":None,"last_event_id":event_id};_save(state)
    return {**snap,"position":state.get("position"),"journal_appended":changed}

def public_snapshot(candles:list[Any],consensus:dict[str,Any])->dict[str,Any]:
    snap=evaluate(candles,consensus);state=_load();rows=journal();closed=[r for r in rows if r.get("action")=="CLOSE_LONG"];wins=[r for r in closed if float(r.get("result_pct") or 0)>0]
    return {**snap,"mode":"SHADOW","position":state.get("position"),"closed_trades":len(closed),"win_rate":round(len(wins)/len(closed)*100,1) if closed else None,"journal":rows[-20:]}
