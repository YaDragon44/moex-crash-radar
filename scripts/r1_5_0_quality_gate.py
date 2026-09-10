from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

VALID_QUALITY={"LIVE","DELAYED","STALE","N/A","BLOCKED_AUTH"}

@dataclass(frozen=True)
class Observation:
    source:str
    event_time:Optional[datetime]
    available_time:Optional[datetime]
    decision_time:datetime
    quality:str
    value:object=None


def validate(o:Observation)->tuple[bool,str]:
    if o.quality not in VALID_QUALITY:return False,"INVALID_QUALITY"
    if not o.source:return False,"MISSING_SOURCE"
    if o.quality in {"N/A","BLOCKED_AUTH"}:
        if o.value is not None:return False,"FAIL_CLOSED_VALUE_REQUIRED_NONE"
        return True,o.quality
    if o.event_time is None or o.available_time is None:return False,"MISSING_TIMESTAMP"
    if o.available_time>o.decision_time:return False,"LOOKAHEAD_AVAILABLE_AFTER_DECISION"
    return True,o.quality


def coverage(observations:list[Observation])->dict:
    if not observations:return {"total":0,"usable":0,"coverage_pct":0.0,"data_ready":False}
    usable=sum(validate(o)[0] and o.quality not in {"N/A","BLOCKED_AUTH","STALE"} for o in observations)
    pct=round(100*usable/len(observations),2)
    return {"total":len(observations),"usable":usable,"coverage_pct":pct,"data_ready":pct>=80.0}


def blocked_futoi(decision_time:Optional[datetime]=None)->Observation:
    return Observation(source="MOEX_FUTOI",event_time=None,available_time=None,decision_time=decision_time or datetime.now(timezone.utc),quality="BLOCKED_AUTH",value=None)
