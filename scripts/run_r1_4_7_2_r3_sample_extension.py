from __future__ import annotations
import json, statistics
from collections import defaultdict
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain, split_of
from run_r1_4_7_regime_engine_redesign import state, FAMILIES

HORIZONS=(1,2,4,8)
COST_BPS=5.0
START='2022-01-01'
END='2026-09-01'

def stats(vals):
    if not vals:return {'n':0}
    s=sorted(vals); n=len(vals); pos=sum(x for x in vals if x>0); neg=-sum(x for x in vals if x<0)
    trim=s[1:-1] if n>=5 else s
    return {'n':n,'mean':round(sum(vals)/n,2),'median':round(statistics.median(vals),2),'positive_pct':round(100*sum(x>0 for x in vals)/n,2),'profit_factor':round(pos/neg,3) if neg else (999.0 if pos else None),'trimmed_mean':round(sum(trim)/len(trim),2) if trim else None,'sum':round(sum(vals),2)}

def sample_split(ts):
    y=int(ts[:4])
    if y<=2024:return 'DEVELOPMENT'
    if y==2025:return 'VALIDATION'
    return 'OOS'

def half(ts):
    return f"{ts[:4]}-H{1 if int(ts[5:7])<=6 else 2}"

def collect():
    events=[]; quality={}
    for fam in FAMILIES:
        try:
            rows,q=build_chain(fam,START,END); quality[fam]=q
        except Exception as exc:
            quality[fam]={'status':'ERROR','error':repr(exc)}; continue
        for i in range(52,len(rows)-max(HORIZONS)):
            side=state(rows,i,'R3_STRUCTURE_EARLY')
            if side not in ('LONG','SHORT'):continue
            ts=rows[i]['begin']; px=float(rows[i]['close'])
            for h in HORIZONS:
                if rows[i+h]['secid']!=rows[i]['secid']:continue
                future=float(rows[i+h]['close'])
                gross=(future/px-1)*10000*(1 if side=='LONG' else -1)
                events.append({'family':fam,'side':side,'signal_time':ts,'split':sample_split(ts),'year':ts[:4],'half':half(ts),'horizon':h,'gross_bps':round(gross,4),'net_bps':round(gross-COST_BPS,4),'secid':rows[i]['secid']})
    return events,quality

def grouped(events,key):
    d=defaultdict(list)
    for e in events:d[e[key]].append(e['net_bps'])
    return {k:stats(v) for k,v in sorted(d.items())}

def classify(v,o):
    n=o.get('n',0); vm=v.get('mean'); om=o.get('mean'); pf=o.get('profit_factor')
    if n>=10 and vm is not None and om is not None and vm>0 and om>0 and (pf or 0)>1:return 'SUPPORTIVE'
    if n>=10 and vm is not None and om is not None and vm<=0 and om<=0:return 'NEGATIVE'
    return 'MIXED'

def sensitivity(es):
    if not es:return {'base':{'n':0}}
    base=stats([e['net_bps'] for e in es]); best=max(es,key=lambda e:e['net_bps'])
    leave_best=stats([e['net_bps'] for e in es if e is not best])
    fams=sorted({e['family'] for e in es})
    loo={f:stats([e['net_bps'] for e in es if e['family']!=f]) for f in fams}
    pos=sorted((e['net_bps'] for e in es if e['net_bps']>0),reverse=True); total=sum(pos)
    return {'base':base,'best_event':best,'leave_best_event_out':leave_best,'leave_one_family_out':loo,'top1_positive_pnl_share_pct':round(100*pos[0]/total,2) if pos and total else None,'top3_positive_pnl_share_pct':round(100*sum(pos[:3])/total,2) if pos and total else None}

def main():
    events,quality=collect(); primary=[e for e in events if e['horizon']==4]
    report={'release':'R1.4.7.2','period':{'start':START,'end':END},'quality':quality,'primary_horizon':4,'cost_bps':COST_BPS,'splits':{},'market_direction':{}}
    for sp in ('DEVELOPMENT','VALIDATION','OOS'):
        es=[e for e in primary if e['split']==sp]
        report['splits'][sp]={'aggregate':stats([e['net_bps'] for e in es]),'by_family':grouped(es,'family'),'by_side':grouped(es,'side'),'by_year':grouped(es,'year'),'by_half':grouped(es,'half')}
    for fam in FAMILIES:
        report['market_direction'][fam]={}
        for side in ('LONG','SHORT'):
            v=stats([e['net_bps'] for e in primary if e['split']=='VALIDATION' and e['family']==fam and e['side']==side])
            o=stats([e['net_bps'] for e in primary if e['split']=='OOS' and e['family']==fam and e['side']==side])
            report['market_direction'][fam][side]={'validation':v,'oos':o,'classification':classify(v,o)}
    oos=[e for e in primary if e['split']=='OOS']; sens=sensitivity(oos); report['sensitivity']=sens
    v=report['splits']['VALIDATION']['aggregate']; o=report['splits']['OOS']['aggregate']
    fam_pos=sum(1 for z in report['splits']['OOS']['by_family'].values() if z.get('mean',0)>0)
    half_pos=sum(1 for z in report['splits']['OOS']['by_half'].values() if z.get('mean',0)>0)
    family_sign_ok=all(z.get('mean',-1)>0 for z in sens.get('leave_one_family_out',{}).values()) if sens.get('leave_one_family_out') else False
    robust=(v.get('mean',-1)>0 and o.get('mean',-1)>0 and (o.get('profit_factor') or 0)>1 and sens.get('leave_best_event_out',{}).get('mean',-1)>0 and family_sign_ok and fam_pos>=2 and half_pos>=2)
    report['gate']={'status':'RESEARCH_CANDIDATE' if robust else 'REJECTED_NON_ROBUST','production':'NO-GO','positive_oos_families':fam_pos,'positive_oos_halves':half_pos,'leave_one_family_sign_stable':family_sign_ok}
    report['diagnostic_horizons']={str(h):stats([e['net_bps'] for e in events if e['split']=='OOS' and e['horizon']==h]) for h in HORIZONS}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/r1_4_7_2_r3_sample_extension.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    Path('artifacts/r1_4_7_2_r3_events.json').write_text(json.dumps(events,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'development':report['splits']['DEVELOPMENT']['aggregate'],'validation':v,'oos':o,'market_direction':report['market_direction'],'sensitivity':sens,'gate':report['gate']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
