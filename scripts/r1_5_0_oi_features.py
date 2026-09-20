from __future__ import annotations
from dataclasses import dataclass
from statistics import median

@dataclass(frozen=True)
class OIFeatures:
    oi_total:float|None
    oi_delta:float|None
    oi_delta_pct:float|None
    oi_percentile:float|None
    price_oi_quadrant:str
    oi_persistence:int|None
    quality:str


def percentile_rank(history:list[float],value:float)->float|None:
    if not history:return None
    return round(100.0*sum(x<=value for x in history)/len(history),2)


def build_oi_features(oi_history:list[float|None],price_return:float|None,quality:str)->OIFeatures:
    if quality in {'N/A','BLOCKED_AUTH','STALE'}:
        return OIFeatures(None,None,None,None,'N/A',None,quality)
    clean=[float(x) for x in oi_history if x is not None]
    if len(clean)<2:
        return OIFeatures(None,None,None,None,'N/A',None,'N/A')
    cur,prev=clean[-1],clean[-2]
    delta=cur-prev
    pct=(delta/prev*100.0) if prev!=0 else None
    changes=[clean[i]-clean[i-1] for i in range(1,len(clean))]
    rank=percentile_rank(changes[:-1],delta) if len(changes)>1 else None
    if price_return is None:
        quad='N/A'
    elif price_return>=0 and delta>=0:
        quad='PRICE_UP_OI_UP'
    elif price_return>=0 and delta<0:
        quad='PRICE_UP_OI_DOWN'
    elif price_return<0 and delta>=0:
        quad='PRICE_DOWN_OI_UP'
    else:
        quad='PRICE_DOWN_OI_DOWN'
    sign=1 if delta>0 else (-1 if delta<0 else 0)
    persistence=0
    for d in reversed(changes):
        ds=1 if d>0 else (-1 if d<0 else 0)
        if ds==sign and sign!=0:persistence+=1
        else:break
    return OIFeatures(cur,delta,round(pct,4) if pct is not None else None,rank,quad,persistence,quality)
