from __future__ import annotations
import json, statistics
from collections import defaultdict
from pathlib import Path
from run_r1_4_5_complete_backtest import build_chain, split_of
from run_r1_4_7_regime_engine_redesign import state, FAMILIES

def stats(vals):
    if not vals:
        return {'n':0}
    s=sorted(vals); n=len(vals)
    med=statistics.median(vals)
    pos=sum(x for x in vals if x>0); neg=-sum(x for x in vals if x<0)
    pf=(pos/neg) if neg else (999.0 if pos else None)
    trim=s[1:-1] if n>=5 else s
    return {
        'n':n,'mean':round(sum(vals)/n,2),'median':round(med,2),
        'positive_pct':round(100*sum(x>0 for x in vals)/n,2),
        'profit_factor':round(pf,3) if pf is not None else None,
        'trimmed_mean':round(sum(trim)/len(trim),2) if trim else None,
        'sum':round(sum(vals),2)
    }

def collect():
    events=[]; quality={}
    for fam in FAMILIES:
        try:
            rows,q=build_chain(fam,'2024-01-01','2026-09-01'); quality[fam]=q
        except Exception as x:
            quality[fam]={'status':'ERROR','error':repr(x)}; continue
        for i in range(52,len(rows)-4):
            st=state(rows,i,'R3_STRUCTURE_EARLY')
            if st not in ('LONG','SHORT'):
                continue
            if rows[i+4]['secid']!=rows[i]['secid']:
                continue
            a=float(rows[i]['close']); b=float(rows[i+4]['close'])
            gross=(b/a-1)*10000*(1 if st=='LONG' else -1)
            net=gross-5
            ts=rows[i]['begin']
            y,m=int(ts[:4]),int(ts[5:7]); qtr=(m-1)//3+1
            events.append({'family':fam,'side':st,'signal_time':ts,'split':split_of(ts),'month':ts[:7],'quarter':f'{y}-Q{qtr}','gross_bps':round(gross,4),'net_bps':round(net,4)})
    return events,quality

def grouped(events,key):
    d=defaultdict(list)
    for e in events:d[e[key]].append(e['net_bps'])
    return {k:stats(v) for k,v in sorted(d.items())}

def sensitivity(events):
    vals=[e['net_bps'] for e in events]
    base=stats(vals)
    if not events:return {'base':base}
    best_i=max(range(len(events)),key=lambda i:events[i]['net_bps'])
    leave_best=stats([v for i,v in enumerate(vals) if i!=best_i])
    fams=sorted({e['family'] for e in events})
    loo_fam={f:stats([e['net_bps'] for e in events if e['family']!=f]) for f in fams}
    positive=[e['net_bps'] for e in events if e['net_bps']>0]
    pos_total=sum(positive)
    ordered=sorted(positive,reverse=True)
    c1=(100*ordered[0]/pos_total) if ordered and pos_total else None
    c3=(100*sum(ordered[:3])/pos_total) if ordered and pos_total else None
    return {'base':base,'best_event':events[best_i],'leave_best_event_out':leave_best,'leave_one_family_out':loo_fam,'top1_positive_pnl_share_pct':round(c1,2) if c1 is not None else None,'top3_positive_pnl_share_pct':round(c3,2) if c3 is not None else None}

def main():
    events,quality=collect()
    report={'release':'R1.4.7.1','quality':quality,'splits':{}}
    for sp in ('VALIDATION','OOS'):
        es=[e for e in events if e['split']==sp]
        report['splits'][sp]={
            'events':es,
            'aggregate':stats([e['net_bps'] for e in es]),
            'by_side':grouped(es,'side'),
            'by_family':grouped(es,'family'),
            'by_month':grouped(es,'month'),
            'by_quarter':grouped(es,'quarter'),
            'sensitivity':sensitivity(es)
        }
    v=report['splits']['VALIDATION']['aggregate']; o=report['splits']['OOS']['aggregate']; sens=report['splits']['OOS']['sensitivity']
    fam_pos=sum(1 for x in report['splits']['OOS']['by_family'].values() if x.get('mean',0)>0)
    fam_n=len(report['splits']['OOS']['by_family'])
    q_pos=sum(1 for x in report['splits']['OOS']['by_quarter'].values() if x.get('mean',0)>0)
    q_n=len(report['splits']['OOS']['by_quarter'])
    robust=(v.get('mean',-1)>0 and o.get('mean',-1)>0 and (o.get('profit_factor') or 0)>1 and
            (sens.get('top1_positive_pnl_share_pct') or 999)<=50 and
            sens.get('leave_best_event_out',{}).get('mean',-1)>0 and fam_pos>=2 and q_pos>=2)
    report['gate']={'status':'RESEARCH_CANDIDATE' if robust else 'REJECTED_NON_ROBUST','positive_oos_families':fam_pos,'oos_family_count':fam_n,'positive_oos_quarters':q_pos,'oos_quarter_count':q_n,'production':'NO-GO'}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/r1_4_7_1_r3_robustness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'validation':report['splits']['VALIDATION']['aggregate'],'oos':o,'sensitivity':sens,'gate':report['gate']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
