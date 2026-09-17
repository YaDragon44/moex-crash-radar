from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

@dataclass(frozen=True)
class CoverageRow:
    family: str
    event_time: datetime
    available_time: datetime
    decision_time: datetime
    quality: str

USABLE={"LIVE","DELAYED"}

def evaluate(rows: Iterable[CoverageRow], authenticated: bool) -> dict:
    if not authenticated:
        return {"status":"BLOCKED_AUTH","data_ready":False,"families":0,"subperiods":0,"m1_unlocked":False,"m2_m3_unlocked":False}
    valid=[r for r in rows if r.quality in USABLE and r.available_time <= r.decision_time]
    families=sorted({r.family for r in valid})
    # Conservative chronology gate: distinct calendar half-years.
    periods=sorted({(r.event_time.year, 1 if r.event_time.month <= 6 else 2) for r in valid})
    ready=len(families)>=2 and len(periods)>=2
    return {"status":"DATA_READY" if ready else "DATA_LIMITED","data_ready":ready,"families":len(families),"subperiods":len(periods),"m1_unlocked":ready,"m2_m3_unlocked":ready}
