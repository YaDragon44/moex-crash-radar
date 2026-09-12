from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUT = Path('data/crypto-radar/derivatives_shadow_replay.json')
BASE = 'https://api.gateio.ws/api/v4'


def finite(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def get_json(path, params):
    url=f"{BASE}{path}?{urlencode(params)}"
    req=Request(url,headers={'Accept':'application/json','User-Agent':'crypto-crowd-radar-r1.7.1'})
    with urlopen(req,timeout=25) as r:
        return json.load(r)


def leverage_risk(price24, oi24):
    if price24 is None or oi24 is None: return None
    if price24>0 and oi24>0: return 80 if oi24>=8 else 70 if oi24>=4 else 55
    if price24<0 and oi24>0: return 90 if oi24>=8 else 80 if oi24>=4 else 65
    if price24<0 and oi24<0: return 55 if price24<=-2 else 45
    if price24>0 and oi24<0: return 30
    return 40


def funding_extreme(funding_pct):
    if funding_pct is None: return None
    a=abs(funding_pct)
    if a<0.01: return 20
    if a<0.03: return 45
    if a<0.06: return 70
    return 90


def positioning_extreme(lsr):
    if lsr is None or lsr<=0: return None
    if 0.90<=lsr<=1.10: return 20
    if 0.75<=lsr<0.90 or 1.10<lsr<=1.30: return 40
    if 0.60<=lsr<0.75 or 1.30<lsr<=1.50: return 65
    return 85


def corr(xs,ys):
    if len(xs)<3: return None
    mx=statistics.fmean(xs); my=statistics.fmean(ys)
    dx=[x-mx for x in xs]; dy=[y-my for y in ys]
    den=(sum(x*x for x in dx)*sum(y*y for y in dy))**0.5
    return None if den==0 else sum(a*b for a,b in zip(dx,dy))/den


def pct_change(a,b):
    return None if a in (None,0) or b is None else (b/a-1)*100


def main():
    now=datetime.now(timezone.utc)
    start=now-timedelta(days=30)
    frm=int(start.timestamp()); to=int(now.timestamp())

    candles=get_json('/futures/usdt/candlesticks',{'contract':'BTC_USDT','from':frm,'to':to,'interval':'1h'})
    stats=get_json('/futures/usdt/contract_stats',{'contract':'BTC_USDT','from':frm,'interval':'1h','limit':1000})
    funding=get_json('/futures/usdt/funding_rate',{'contract':'BTC_USDT','from':frm,'to':to,'limit':1000})

    price={int(float(x['t'])):finite(x.get('c')) for x in candles if isinstance(x,dict) and finite(x.get('t')) is not None}
    stat={int(float(x['time'])):x for x in stats if isinstance(x,dict) and finite(x.get('time')) is not None}
    fr=sorted((int(float(x['t'])),finite(x.get('r'))) for x in funding if isinstance(x,dict) and finite(x.get('t')) is not None and finite(x.get('r')) is not None)

    times=sorted(set(price)&set(stat))
    rows=[]; fidx=0; last_f=None; last_ft=None
    for t in times:
        while fidx<len(fr) and fr[fidx][0]<=t:
            last_ft,last_f=fr[fidx]; fidx+=1
        # Funding is periodic; do not carry it indefinitely.
        funding_pct=last_f*100 if last_f is not None and last_ft is not None and t-last_ft<=12*3600 else None
        p=price.get(t); p24=price.get(t-24*3600); pnext=price.get(t+24*3600)
        s=stat[t]; oi=finite(s.get('open_interest_usd')); lsr=finite(s.get('lsr_account'))
        prevs=stat.get(t-24*3600); oi_prev=finite(prevs.get('open_interest_usd')) if prevs else None
        price24=pct_change(p24,p); oi24=pct_change(oi_prev,oi)
        lev=leverage_risk(price24,oi24); fund=funding_extreme(funding_pct); pos=positioning_extreme(lsr)
        comps=[(lev,30),(fund,15),(pos,15)]
        available=[(v,w) for v,w in comps if v is not None]
        shadow=round(sum(v*w for v,w in available)/sum(w for _,w in available),2) if len(available)==3 else None
        forward24=pct_change(p,pnext)
        rows.append({'t':t,'btc_price':p,'price_change_24h_pct':price24,'oi_change_24h_pct':oi24,'funding_pct':funding_pct,'long_short_ratio':lsr,'leverage_component':lev,'funding_component':fund,'positioning_component':pos,'shadow_score':shadow,'btc_forward_24h_pct':forward24})

    scored=[r for r in rows if r['shadow_score'] is not None]
    closed=[r for r in scored if r['btc_forward_24h_pct'] is not None]
    scores=[r['shadow_score'] for r in closed]
    future_losses=[-r['btc_forward_24h_pct'] for r in closed]
    ordered=sorted(closed,key=lambda r:r['shadow_score'])
    q=max(1,len(ordered)//5) if ordered else 0
    low=ordered[:q] if q else []
    high=ordered[-q:] if q else []
    mean=lambda a,k: round(statistics.fmean(r[k] for r in a),4) if a else None

    out={
      'release':'R1.7.1 Derivatives Shadow Replay',
      'generated_at':now.isoformat(),
      'window_days':30,
      'status':'SHADOW_ONLY',
      'model_semantics':'Normalized replay of existing live derivative Risk components only: leverage 30, funding extremity 15, positioning extremity 15. Not comparable to full live Risk Score because Market Stress and Liquidity Context are absent.',
      'rows':len(rows),
      'scored_rows':len(scored),
      'closed_24h_rows':len(closed),
      'coverage_pct':round(len(scored)/len(rows)*100,1) if rows else 0,
      'metrics':{
        'mean_shadow_score':round(statistics.fmean(r['shadow_score'] for r in scored),2) if scored else None,
        'p90_shadow_score':round(sorted(r['shadow_score'] for r in scored)[max(0,math.ceil(len(scored)*0.9)-1)],2) if scored else None,
        'corr_shadow_score_vs_next24h_loss':round(corr(scores,future_losses),4) if corr(scores,future_losses) is not None else None,
        'lowest_quintile_avg_next24h_return_pct':mean(low,'btc_forward_24h_pct'),
        'highest_quintile_avg_next24h_return_pct':mean(high,'btc_forward_24h_pct'),
        'highest_minus_lowest_quintile_return_pct':round(mean(high,'btc_forward_24h_pct')-mean(low,'btc_forward_24h_pct'),4) if high and low else None,
      },
      'gate':{
        'data_quality':'PASS' if rows and len(scored)/len(rows)>=0.95 else 'FAIL',
        'full_model_validation':'NO-GO',
        'threshold_calibration':'PROHIBITED',
        'interpretation':'Diagnostic only. A positive score-vs-future-loss correlation is directionally desirable, but 30 days and partial factors are insufficient for investment validation.'
      },
      'records':rows
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'rows':out['rows'],'coverage':out['coverage_pct'],'metrics':out['metrics'],'gate':out['gate']},ensure_ascii=False))


if __name__=='__main__':
    main()
