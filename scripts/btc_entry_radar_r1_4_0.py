from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional

STATES=("NO_TRADE","WATCH","ARMED","LONG_READY","MANAGE")

@dataclass
class EntryRadarInput:
    fgi: Optional[float]
    price_confirm_4h: Optional[bool]
    new_local_low_4h: Optional[bool]
    oi_regime: str
    stop_atr: Optional[float]
    data_ready: bool
    position_open: bool=False

@dataclass
class EntryRadarOutput:
    state:str; action:str; standard_size:float; why:list[str]; invalidation:str

def evaluate(x:EntryRadarInput)->EntryRadarOutput:
    if x.position_open:
        return EntryRadarOutput("MANAGE","MANAGE POSITION",0.0,["Position already open","Use structure/stop for exit","Do not re-enter from crowd score alone"],"4H structure failure or protective stop")
    if x.fgi is not None and x.fgi>60:
        why=["Crowd is in Greed zone","MVP seeks asymmetric fear entries","New long lacks crowd discount"]
        if not x.data_ready: why.append("Quality coverage is partial; verdict is veto-only")
        return EntryRadarOutput("NO_TRADE","DO NOT CHASE",0.0,why,"F&G returns to <=35 and full Quality Gate is restored")
    if not x.data_ready or x.fgi is None or x.price_confirm_4h is None or x.new_local_low_4h is None:
        return EntryRadarOutput("NO_TRADE","WAIT",0.0,["Quality Gate failed","Required entry input is STALE/N/A","Missing data cannot create a positive setup"],"Data quality restored")
    if x.stop_atr is None or x.stop_atr<=0 or x.stop_atr>2:
        return EntryRadarOutput("NO_TRADE","WAIT",0.0,["Risk gate failed","Stop distance is invalid or >2 ATR","Entry is too late or structure unclear"],"Valid stop <=2 ATR")
    if x.oi_regime=="OVERHEATED":
        return EntryRadarOutput("NO_TRADE","DO NOT CHASE",0.0,["Leverage build-up is overheated","Long squeeze risk elevated","OI is a risk modifier, not a buy trigger"],"Leverage normalizes")
    if x.new_local_low_4h:
        return EntryRadarOutput("WATCH" if x.fgi<=35 else "NO_TRADE","WAIT",0.0,["Fear zone is present" if x.fgi<=35 else "Crowd gate is weak","BTC still makes a local low","Price reversal is not confirmed"],"BTC stops making local lows")
    if x.fgi<=35 and not x.price_confirm_4h:
        return EntryRadarOutput("ARMED","WAIT FOR 4H CONFIRMATION",0.0,["F&G permits long search","BTC has stopped making a local low","4H breakout confirmation is still absent"],"New local low")
    if x.fgi<=35 and x.price_confirm_4h:
        size=1.0 if x.fgi<=25 and x.oi_regime=="DELEVERAGING" else 0.75
        if x.oi_regime in {"MODERATE_BUILD","N/A"}: size=0.5
        return EntryRadarOutput("LONG_READY","SELECTIVE LONG",size,["Fear/Crowd Gate passed","4H price reversal confirmed",f"OI regime: {x.oi_regime}"],"New 4H local low / protective stop")
    return EntryRadarOutput("NO_TRADE","WAIT",0.0,["No validated MVP setup","Crowd/price combination is insufficient","Capital preservation has priority"],"Wait for next setup")

def to_dict(x:EntryRadarInput): return {"input":asdict(x),"output":asdict(evaluate(x))}
