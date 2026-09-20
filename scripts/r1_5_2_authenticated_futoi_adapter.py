from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

VALID_GROUPS={'FIZ','YUR'}

@dataclass(frozen=True)
class FUTOIRow:
    source:str
    ticker:str
    clgroup:str
    pos:float
    pos_long:float
    pos_short:float
    event_time:datetime
    available_time:datetime
    decision_time:datetime
    quality:str

@dataclass(frozen=True)
class AdapterResult:
    quality:str
    rows:tuple[FUTOIRow,...]
    reason:str|None=None


def blocked_auth(reason:str='credentials/subscription unavailable')->AdapterResult:
    return AdapterResult('BLOCKED_AUTH',tuple(),reason)


def parse_dt(value:str)->datetime:
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def adapt_futoi_rows(raw_rows:Iterable[dict],decision_time:datetime,authenticated:bool)->AdapterResult:
    if not authenticated:
        return blocked_auth()
    out=[]; seen=set()
    required={'TICKER','CLGROUP','POS','POS_LONG','POS_SHORT','MOMENT','SYSTIME'}
    for raw in raw_rows:
        if not required.issubset(raw):
            continue
        group=str(raw['CLGROUP']).upper()
        if group not in VALID_GROUPS:
            continue
        event_time=parse_dt(str(raw['MOMENT']))
        available_time=parse_dt(str(raw['SYSTIME']))
        if available_time>decision_time:
            continue
        key=(str(raw['TICKER']),group,event_time,available_time)
        if key in seen:
            continue
        seen.add(key)
        out.append(FUTOIRow('MOEX_FUTOI',str(raw['TICKER']),group,float(raw['POS']),float(raw['POS_LONG']),float(raw['POS_SHORT']),event_time,available_time,decision_time,'LIVE'))
    if not out:
        return AdapterResult('N/A',tuple(),'no usable point-in-time rows')
    out.sort(key=lambda r:(r.ticker,r.event_time,r.available_time,r.clgroup))
    return AdapterResult('LIVE',tuple(out),None)


def paired_positioning(rows:Iterable[FUTOIRow])->list[dict]:
    buckets={}
    for r in rows:
        buckets.setdefault((r.ticker,r.event_time,r.available_time),{})[r.clgroup]=r
    result=[]
    for (ticker,event_time,available_time),g in sorted(buckets.items()):
        if set(g)!={'FIZ','YUR'}:
            continue
        fiz,yur=g['FIZ'],g['YUR']
        result.append({
            'ticker':ticker,'event_time':event_time,'available_time':available_time,
            'fiz_net':fiz.pos_long+fiz.pos_short,
            'yur_net':yur.pos_long+yur.pos_short,
            'fiz_gross':fiz.pos_long+abs(fiz.pos_short),
            'yur_gross':yur.pos_long+abs(yur.pos_short),
            'quality':'LIVE'
        })
    return result
