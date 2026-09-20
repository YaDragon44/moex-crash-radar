from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

@dataclass(frozen=True)
class FutoiSnapshot:
    ticker:str
    clgroup:str
    pos:float|None
    pos_long:float|None
    pos_short:float|None
    moment:datetime|None
    systime:datetime|None
    quality:str
    source:str='MOEX_FUTOI'

class FutoiAdapter(Protocol):
    def get_history(self,ticker:str,start:datetime,end:datetime)->list[FutoiSnapshot]: ...

class BlockedAuthFutoiAdapter:
    """Fail-closed adapter used when authenticated MOEX FUTOI history is unavailable."""
    def get_history(self,ticker:str,start:datetime,end:datetime)->list[FutoiSnapshot]:
        return [FutoiSnapshot(ticker=ticker,clgroup='N/A',pos=None,pos_long=None,pos_short=None,moment=None,systime=None,quality='BLOCKED_AUTH')]

def validate_snapshot(x:FutoiSnapshot,decision_time:datetime)->tuple[bool,str]:
    if x.quality=='BLOCKED_AUTH':
        clean=all(v is None for v in (x.pos,x.pos_long,x.pos_short,x.moment,x.systime))
        return (clean,'BLOCKED_AUTH' if clean else 'INVALID_BLOCKED_AUTH_PAYLOAD')
    if x.quality not in {'LIVE','DELAYED','STALE','N/A'}:return False,'INVALID_QUALITY'
    if x.quality=='N/A':
        return (x.pos is None and x.pos_long is None and x.pos_short is None,'N/A')
    if x.moment is None or x.systime is None:return False,'MISSING_TIMESTAMP'
    if x.systime>decision_time:return False,'LOOKAHEAD_SYSTIME_AFTER_DECISION'
    if x.clgroup not in {'FIZ','YUR'}:return False,'INVALID_CLGROUP'
    return True,x.quality
