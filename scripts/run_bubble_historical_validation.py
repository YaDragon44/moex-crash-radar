from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from moex_crash_radar.bubble_history import historical_bubble_points
from moex_crash_radar.bubble_validation import BubbleEpisode, validate_bubble
from moex_crash_radar.bull_history import historical_bull_points
from moex_crash_radar.bull_bubble_transition import build_bull_bubble_transitions
from moex_crash_radar.calibration import signal_event_indices
from moex_crash_radar.history import build_daily_evidence
from moex_crash_radar.live_gate import CALIBRATED_EXIT_GATE
from moex_crash_radar.moex import fetch_index_history, fetch_share_history

UNIVERSE=("SBER","SBERP","LKOH","GAZP","YDEX","T","X5","GMKN","NVTK","ROSN","TATN","TATNP","PLZL","CHMF","NLMK","ALRS","MOEX","MTSS","PHOR","IRAO","HYDR","AFLT","VKCO","OZON")
EPISODES=(BubbleEpisode("COVID_2020","2020-01-10","2020-03-18"),BubbleEpisode("FEB_2022","2022-01-10","2022-02-24"),BubbleEpisode("SEP_2022","2022-08-01","2022-10-10"),BubbleEpisode("CORRECTION_2024","2024-05-01","2024-09-03"))

def _days(a,b): return (date.fromisoformat(b)-date.fromisoformat(a)).days

def main():
    start,end="2019-09-01","2026-08-27"
    index=fetch_index_history("IMOEX",start=start,end=end); universe={}; failures={}
    for secid in UNIVERSE:
        try:
            rows=fetch_share_history(secid,start=start,end=end)
            if len(rows)>=60: universe[secid]=rows
            else: failures[secid]=f"only {len(rows)} candles"
        except Exception as exc: failures[secid]=f"{type(exc).__name__}: {exc}"
    evidence=build_daily_evidence(index,universe,min_equity_coverage=.50,warmup=60)
    bubble=historical_bubble_points(evidence); bull=historical_bull_points(evidence)
    transitions=build_bull_bubble_transitions(bull,bubble)
    p=CALIBRATED_EXIT_GATE
    exit_indices=signal_event_indices(evidence,score_threshold=p.score_threshold,confirmations=p.confirmations,persistence=p.persistence,max_5d_return_pct=p.max_5d_return_pct,cooldown_rows=p.cooldown_rows,require_breadth_volume=p.require_breadth_volume,rearm_clear_rows=p.rearm_clear_rows)
    exit_days=[evidence[i].day for i in exit_indices]
    candidates=[validate_bubble(evidence,bubble,EPISODES,threshold=t,exit_event_days=exit_days) for t in (45.,50.,55.,60.,65.,70.,75.)]
    div_states={"BULL_BUBBLE_DIVERGENCE","DISTRIBUTION_WATCH","BREAKDOWN_RISK"}
    div_days=[x.day for x in transitions if x.state in div_states]
    episode_stats=[]
    for ep in EPISODES:
        # Bubble/strength deterioration may precede the named crisis window by 120 calendar days.
        window_start=date.fromisoformat(ep.start).toordinal()-120
        ds=[d for d in div_days if window_start<=date.fromisoformat(d).toordinal()<=date.fromisoformat(ep.trough).toordinal()]
        first=ds[0] if ds else None
        exits=[d for d in exit_days if ep.start<=d<=ep.trough]
        first_exit=exits[0] if exits else None
        episode_stats.append({"name":ep.name,"first_divergence":first,"first_exit":first_exit,"lead_to_trough_days":_days(first,ep.trough) if first else None,"advance_vs_exit_days":_days(first,first_exit) if first and first_exit else None})
    scored_b=[x for x in bubble if x.score is not None]; scored_u=[x for x in bull if x.score is not None]
    payload={"release":"R0.5.4.2 Bull × Bubble Transition Replay","status":"RESEARCH_ONLY","source":"MOEX ISS","range":{"start":start,"end":end},"data_gate":{"evidence_rows":len(evidence),"bubble_scored_rows":len(scored_b),"bull_scored_rows":len(scored_u),"usable_equities":len(universe),"failed_equities":failures},"methodology":{"point_in_time":True,"look_ahead":False,"live_exit_gate_unchanged":True,"divergence_states":sorted(div_states),"pre_crisis_observation_days":120,"warning":"Bull and Bubble historical models remain research proxies; no production action is changed."},"frozen_exit_gate":asdict(p),"exit_event_days":exit_days,"divergence_event_days":div_days,"episode_transition_stats":episode_stats,"bubble_candidates":[asdict(x) for x in candidates]}
    out=Path("artifacts/bubble_historical_validation.json"); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
