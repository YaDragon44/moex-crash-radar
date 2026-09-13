#!/usr/bin/env python3
from __future__ import annotations
import json, re, ssl
from collections import Counter
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from statistics import mean, median
from urllib.request import Request, urlopen

from ofz_strategy_engine import simulate_path_strategy, regime

CURRENT=Path('web/ofz-radar/data/current.json')
OUT=Path('web/ofz-radar/data/historical-validation.json')
UA='Mozilla/5.0 OFZ-Signal-Radar/0.5.6'
POLICIES={
    'BASELINE_100_60_25':{'A':1.0,'B':1.0,'C':1.0,'D':.60,'E':.25},
    'LATE_EXIT_100_80_50':{'A':1.0,'B':1.0,'C':1.0,'D':.80,'E':.50},
    'MILD_EXIT_100_90_65':{'A':1.0,'B':1.0,'C':1.0,'D':.90,'E':.65},
    'EARLY_CUT_100_85_60_25':{'A':1.0,'B':1.0,'C':.85,'D':.60,'E':.25},
}
START_YEARS=list(range(2003,2022,2))

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=[]; self.in_cell=False
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        if tag in ('td','th'): self.in_cell=True; self.cell=[]
    def handle_data(self,data):
        if self.in_cell:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.in_cell:
            self.row.append(' '.join(''.join(self.cell).split()));self.in_cell=False
        if tag=='tr' and self.row:self.rows.append(self.row)

def get(url,timeout=25):
    req=Request(url,headers={'User-Agent':UA,'Accept':'text/html,*/*'})
    with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:
        return r.read().decode('utf-8','replace')

def num(s):
    if s is None:return None
    m=re.search(r'-?\d+(?:[\.,]\d+)?',str(s).replace('\xa0',' ').replace(' ',''))
    return float(m.group().replace(',','.')) if m else None

def fetch_curve_point(target:date):
    d=target
    for _ in range(10):
        ds=d.strftime('%d.%m.%Y')
        p=TableParser();p.feed(get(f'https://www.cbr.ru/eng/hd_base/zcyc_params/zcyc/?DateTo={ds}'))
        for r in p.rows:
            vals=[num(x) for x in r]
            vals=[x for x in vals if x is not None]
            if len(vals)>=12:
                ys=vals[-12:]
                if all(0<x<60 for x in ys):
                    return {'date':d,'y10':float(ys[8])}
        d-=timedelta(days=1)
    raise RuntimeError(f'CBR curve unavailable near {target.isoformat()}')

def fetch_annual_history(last_year:int):
    rows=[]
    for y in range(2003,last_year+1):
        rows.append(fetch_curve_point(date(y,1,15)))
    if len(rows)<20:raise RuntimeError(f'CBR annual history too short: {len(rows)} rows')
    return rows

def historical_windows(rows):
    by_year={r['date'].year:r for r in rows}
    out=[]
    for y in START_YEARS:
        pts=[by_year.get(y+k) for k in range(6)]
        if all(pts):
            out.append({
                'name':f'{y}-{y+5}',
                'dates':[p['date'].isoformat() for p in pts],
                'path':[round(p['y10'],4) for p in pts],
                'regimes':[regime(p['y10']) for p in pts],
            })
    if len(out)<8:raise RuntimeError(f'not enough historical windows: {len(out)}')
    return out

def main():
    cur=json.loads(CURRENT.read_text(encoding='utf-8'))
    portfolio=cur.get('portfolio') or {};bonds=cur.get('bonds') or [];valuation=cur.get('valuationDate')
    if not portfolio.get('ready') or len(bonds)!=4 or not valuation:raise SystemExit('production snapshot not ready')
    valuation_date=datetime.strptime(valuation,'%Y-%m-%d').date()
    rows=fetch_annual_history(valuation_date.year)
    windows=historical_windows(rows)
    regime_counts=Counter(regime(r['y10']) for r in rows)
    summaries=[];window_results=[]
    for w in windows:
        hold=simulate_path_strategy(portfolio,bonds,valuation,w['path'],False)
        if not hold.get('ready') or not hold.get('economicSanity'):raise RuntimeError(f"hold failed {w['name']}")
        wr={'name':w['name'],'dates':w['dates'],'path':w['path'],'regimes':w['regimes'],'buyHold':{'terminalValue':hold['terminalValue'],'cagr':hold['cagr'],'maxDrawdown':hold['maxDrawdown']},'policies':{}}
        for name,policy in POLICIES.items():
            active=simulate_path_strategy(portfolio,bonds,valuation,w['path'],True,exposure_policy=policy)
            if not active.get('ready') or not active.get('economicSanity'):raise RuntimeError(f'{name} failed {w["name"]}')
            wr['policies'][name]={
                'terminalValue':active['terminalValue'],'cagr':active['cagr'],'maxDrawdown':active['maxDrawdown'],'turnoverPct':active['turnoverPct'],
                'deltaTerminal':active['terminalValue']-hold['terminalValue'],'deltaCagr':active['cagr']-hold['cagr'],
                'drawdownImprovement':active['maxDrawdown']-hold['maxDrawdown'],
            }
        window_results.append(wr)
    for name,policy in POLICIES.items():
        vals=[w['policies'][name] for w in window_results]
        deltas=[x['deltaTerminal'] for x in vals];dds=[x['drawdownImprovement'] for x in vals];turn=[x['turnoverPct'] for x in vals]
        summaries.append({
            'name':name,'policy':policy,'windows':len(vals),
            'avgDeltaTerminal':mean(deltas),'medianDeltaTerminal':median(deltas),'winRateVsHold':sum(1 for x in deltas if x>0)/len(deltas),
            'avgDrawdownImprovement':mean(dds),'drawdownImprovementWinRate':sum(1 for x in dds if x>1e-9)/len(dds),
            'avgTurnoverPct':mean(turn),'worstDeltaTerminal':min(deltas),'bestDeltaTerminal':max(deltas),
        })
    best_return=max(summaries,key=lambda x:x['avgDeltaTerminal'])['name']
    best_risk=max(summaries,key=lambda x:x['avgDrawdownImprovement'])['name']
    report={
        'version':'0.5.6','sourceVersion':cur.get('version'),'valuationDate':valuation,'status':'PASS',
        'historySource':'CBR Russian Government Bond Zero Coupon Yield Curve','historyPoints':len(rows),
        'historyFrom':rows[0]['date'].isoformat(),'historyTo':rows[-1]['date'].isoformat(),
        'windowMethod':'10 rolling 5Y historical 10Y-yield paths; start every 2 years; annual CBR points near Jan-15',
        'validationType':'HISTORICAL_YIELD_PATH_REPLAY_PROXY','regimeObservationCounts':dict(regime_counts),
        'windows':window_results,'policies':summaries,'bestAvgReturnProxy':best_return,'bestAvgDrawdownProxy':best_risk,
        'decision':'NO_PRODUCTION_CHANGE',
        'reason':'Historical CBR yield-path replay improves evidence, but current-basket P&L before issue dates is a repricing/cashflow proxy, not a true MOEX price backtest. Require common-life MOEX quote backtest before changing production thresholds.',
        'limitations':['Current four-bond basket did not exist over the full CBR history.','Historical CBR 10Y paths are replayed from the current valuation date through the current-basket cashflow engine.','Protective sleeve yield is 0%; taxes, commissions and slippage are excluded.','This validates regime-policy behavior, not realized historical returns of these exact securities.'],
        'assumptions':{'protectiveSleeveYield':0.0,'taxes':False,'commissions':False,'slippage':False},
        'nextTask':'R0.5.7 Common-Life MOEX Quote Backtest'
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"OFZ R0.5.6 HISTORICAL REGIME VALIDATION: PASS points={len(rows)} windows={len(windows)} bestReturn={best_return} bestRisk={best_risk}")
    for x in summaries:print(f"{x['name']}: avgDelta={x['avgDeltaTerminal']:.0f} winRate={x['winRateVsHold']:.0%} avgDDimp={x['avgDrawdownImprovement']:.4f} turnover={x['avgTurnoverPct']:.2f}")

if __name__=='__main__':main()
