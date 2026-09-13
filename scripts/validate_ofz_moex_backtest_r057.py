#!/usr/bin/env python3
from __future__ import annotations
import json, re, ssl
from collections import defaultdict
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from math import floor
from pathlib import Path
from urllib.request import Request, urlopen

CURRENT=Path('web/ofz-radar/data/current.json')
OUT=Path('web/ofz-radar/data/moex-backtest.json')
UA='Mozilla/5.0 OFZ-Signal-Radar/0.5.7'
SECIDS={'26254':'SU26254RMFS1','26253':'SU26253RMFS3','26247':'SU26247RMFS5','26248':'SU26248RMFS3'}
WEIGHTS={'26254':.47,'26253':.29,'26247':.12,'26248':.12}
TERMS=[.25,.5,.75,1,2,3,5,7,10,15,20,30]
POLICIES={
    'BUY_HOLD':{'A':1.0,'B':1.0,'C':1.0,'D':1.0,'E':1.0},
    'BASELINE_100_60_25':{'A':1.0,'B':1.0,'C':1.0,'D':.60,'E':.25},
    'LATE_EXIT_100_80_50':{'A':1.0,'B':1.0,'C':1.0,'D':.80,'E':.50},
    'MILD_EXIT_100_90_65':{'A':1.0,'B':1.0,'C':1.0,'D':.90,'E':.65},
    'EARLY_CUT_100_85_60_25':{'A':1.0,'B':1.0,'C':.85,'D':.60,'E':.25},
}

class TableParser(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=[];self.in_cell=False
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.in_cell=True;self.cell=[]
    def handle_data(self,data):
        if self.in_cell:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.in_cell:self.row.append(' '.join(''.join(self.cell).split()));self.in_cell=False
        if tag=='tr' and self.row:self.rows.append(self.row)

def get(url,timeout=30):
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/html,*/*'})
    with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:return r.read().decode('utf-8','replace')

def num(x):
    if x is None:return None
    try:return float(str(x).replace(',','.'))
    except (TypeError,ValueError):
        m=re.search(r'-?\d+(?:[\.,]\d+)?',str(x));return float(m.group().replace(',','.')) if m else None

def block_rows(obj,name):
    b=obj.get(name) or {};cols=b.get('columns') or [];return [dict(zip(cols,row)) for row in (b.get('data') or [])]

def pick(row,*names):
    for n in names:
        if row.get(n) is not None:
            v=num(row.get(n))
            if v is not None:return v
    return None

def fetch_history(secid,from_date='2024-01-01',till_date='2099-12-31'):
    out=[];start=0
    while True:
        url=(f'https://iss.moex.com/iss/history/engines/stock/markets/bonds/boards/TQOB/securities/{secid}.json'
             f'?iss.meta=off&iss.only=history&from={from_date}&till={till_date}&start={start}')
        obj=json.loads(get(url));rows=block_rows(obj,'history')
        if not rows:break
        for r in rows:
            d=r.get('TRADEDATE') or r.get('tradedate');clean=pick(r,'CLOSE','LEGALCLOSEPRICE','MARKETPRICE3','MARKETPRICE2','WAPRICE','MARKETPRICE','PREVPRICE')
            ai=pick(r,'ACCINT','ACCRUEDINT');face=pick(r,'FACEVALUE')
            if d and clean and clean>0:
                out.append({'date':str(d)[:10],'clean':clean,'ai':ai,'face':face,'volume':pick(r,'VOLUME','VALUE')})
        start+=len(rows)
        if len(rows)<100:break
        if start>5000:raise RuntimeError(f'{secid}: history pagination guard')
    ded={x['date']:x for x in out};return [ded[k] for k in sorted(ded)]

def fetch_coupons(secid):
    obj=json.loads(get(f'https://iss.moex.com/iss/securities/{secid}/bondization.json?iss.meta=off&iss.only=coupons'))
    out=[]
    for r in block_rows(obj,'coupons'):
        d=r.get('coupondate') or r.get('COUPONDATE') or r.get('date') or r.get('DATE')
        v=pick(r,'value','VALUE','couponvalue','COUPONVALUE')
        if d and re.match(r'^\d{4}-\d{2}-\d{2}$',str(d)) and v is not None:out.append({'date':str(d),'value':v})
    ded={x['date']:x for x in out};return [ded[k] for k in sorted(ded)]

def cbr_y10(target):
    d=datetime.strptime(target,'%Y-%m-%d').date()
    for _ in range(10):
        ds=d.strftime('%d.%m.%Y');p=TableParser();p.feed(get(f'https://www.cbr.ru/eng/hd_base/zcyc_params/zcyc/?DateTo={ds}'))
        for row in p.rows:
            vals=[num(x) for x in row];vals=[x for x in vals if x is not None]
            if len(vals)>=12:
                ys=[float(x) for x in vals[-12:]]
                if all(0<x<60 for x in ys) and not all(abs(ys[i]-TERMS[i])<.001 for i in range(12)):return {'date':d.isoformat(),'y10':ys[8]}
        d-=timedelta(days=1)
    raise RuntimeError(f'CBR 10Y unavailable near {target}')

def regime(y):return 'A' if y>=16 else 'B' if y>=14 else 'C' if y>=12 else 'D' if y>=10 else 'E'

def monthly_dates(common):
    by_month={}
    for ds in sorted(common):by_month[ds[:7]]=ds
    dates=sorted(by_month.values())
    if common:
        first=min(common);last=max(common)
        if first not in dates:dates=[first]+dates
        if last not in dates:dates=dates+[last]
    return sorted(set(dates))

def full_price(row,face_fallback):
    face=row.get('face') or face_fallback;ai=row.get('ai')
    if face is None or ai is None:return None
    return face*row['clean']/100+ai

def coupons_between(coupons,prev_ds,ds):
    return [x for x in coupons if prev_ds < x['date'] <= ds]

def run_policy(name,policy,dates,panel,coupons,faces,yields,capital=1_000_000):
    first=dates[0];qty={s:0 for s in WEIGHTS};cash=float(capital);turnover=0.0;coupon_cash=0.0;actions=[];peak=capital;max_dd=0.0
    def mark(ds):
        vals={};bond=0.0
        for s,q in qty.items():
            fp=full_price(panel[s][ds],faces[s])
            if fp is None:raise RuntimeError(f'{s}: full price unavailable {ds}')
            vals[s]={'fp':fp,'value':q*fp};bond+=q*fp
        return {'values':vals,'bondValue':bond,'total':bond+cash}
    def buy_to_target(ds,target):
        nonlocal cash,turnover
        for _ in range(10000):
            mv=mark(ds);desired=mv['total']*target;need=max(0.0,desired-mv['bondValue'])
            if need<=1:break
            pick=None;best=-1e100
            for s,w in WEIGHTS.items():
                cost=mv['values'][s]['fp'];deficit=mv['total']*target*w-mv['values'][s]['value']
                if cost<=cash and cost<=need+max(cost,1) and deficit>best:best=deficit;pick=(s,cost)
            if not pick:break
            s,cost=pick;qty[s]+=1;cash-=cost;turnover+=cost
    def sell_to_target(ds,target,y):
        nonlocal cash,turnover
        mv=mark(ds);desired=mv['total']*target
        if mv['bondValue']<=desired+1:return
        ratio=min(1.0,max(0.0,(mv['bondValue']-desired)/mv['bondValue']));sold=0.0
        for s in qty:
            n=floor(qty[s]*ratio)
            if n<=0:continue
            proceeds=n*mv['values'][s]['fp'];qty[s]-=n;cash+=proceeds;sold+=proceeds
        if sold>0:turnover+=sold;actions.append({'date':ds,'y10':y,'regime':regime(y),'targetExposure':target,'sold':sold})
    y0=yields[first];target0=policy[regime(y0)];buy_to_target(first,target0);timeline=[];prev=first
    mv=mark(first);peak=max(peak,mv['total']);max_dd=min(max_dd,mv['total']/peak-1);timeline.append({'date':first,'y10':y0,'regime':regime(y0),'targetExposure':target0,'value':mv['total']})
    for ds in dates[1:]:
        for s in qty:
            for cp in coupons_between(coupons[s],prev,ds):
                received=qty[s]*cp['value'];cash+=received;coupon_cash+=received
        y=yields[ds];target=policy[regime(y)];sell_to_target(ds,target,y);buy_to_target(ds,target);mv=mark(ds);peak=max(peak,mv['total']);max_dd=min(max_dd,mv['total']/peak-1);timeline.append({'date':ds,'y10':y,'regime':regime(y),'targetExposure':target,'value':mv['total']});prev=ds
    final=mark(dates[-1]);return {'name':name,'terminalValue':final['total'],'returnPct':final['total']/capital-1,'maxDrawdown':max_dd,'turnoverPct':turnover/capital,'couponCash':coupon_cash,'cash':cash,'bondValue':final['bondValue'],'actions':actions,'timeline':timeline,'finalQty':qty}

def main():
    cur=json.loads(CURRENT.read_text(encoding='utf-8'));valuation=cur.get('valuationDate');bonds=cur.get('bonds') or []
    faces={str(b['secid']):float(b.get('faceValue') or 1000) for b in bonds}
    hist={};coupons={}
    for label,secid in SECIDS.items():
        hist[label]=fetch_history(secid,'2024-01-01',valuation);coupons[label]=fetch_coupons(secid)
        if not hist[label]:raise RuntimeError(f'{label}: no MOEX history')
    common=set(x['date'] for x in hist['26254'])
    for s in ('26253','26247','26248'):common&={x['date'] for x in hist[s]}
    if len(common)<20:raise RuntimeError(f'common MOEX history too short: {len(common)} days')
    dates=monthly_dates(common);maps={s:{x['date']:x for x in rows} for s,rows in hist.items()};panel={s:{d:maps[s][d] for d in dates} for s in maps}
    # Require actual accrued interest availability on every selected observation.
    missing=[f'{s}:{d}' for s in panel for d,r in panel[s].items() if r.get('ai') is None]
    if missing:raise RuntimeError('MOEX accrued interest missing: '+','.join(missing[:5]))
    yields={d:cbr_y10(d)['y10'] for d in dates}
    if max(yields.values())-min(yields.values())<.5:raise RuntimeError('common-life 10Y path has insufficient variance')
    results={name:run_policy(name,p,dates,panel,coupons,faces,yields) for name,p in POLICIES.items()};hold=results['BUY_HOLD']
    comparisons=[]
    for name in POLICIES:
        if name=='BUY_HOLD':continue
        r=results[name];comparisons.append({'name':name,'deltaTerminal':r['terminalValue']-hold['terminalValue'],'drawdownImprovement':r['maxDrawdown']-hold['maxDrawdown'],'turnoverPct':r['turnoverPct'],'terminalValue':r['terminalValue'],'maxDrawdown':r['maxDrawdown']})
    best_return=max(comparisons,key=lambda x:x['deltaTerminal'])['name'];best_risk=max(comparisons,key=lambda x:x['drawdownImprovement'])['name']
    report={'version':'0.5.7','status':'PASS','valuationDate':valuation,'validationType':'COMMON_LIFE_MOEX_REAL_QUOTE_BACKTEST','dataSource':'MOEX ISS history + MOEX bondization coupons + CBR 10Y','commonFrom':min(common),'commonTo':max(common),'commonTradingDays':len(common),'monthlyObservations':len(dates),'dates':dates,'y10':yields,'bondHistoryRows':{s:len(v) for s,v in hist.items()},'couponRows':{s:len(v) for s,v in coupons.items()},'results':results,'comparisons':comparisons,'bestReturnVsHold':best_return,'bestDrawdownVsHold':best_risk,'decision':'NO_PRODUCTION_CHANGE','reason':'Common-life realized quote history is still short; use results as validation evidence, not as sufficient basis for changing production thresholds.','assumptions':{'taxes':False,'commissions':False,'slippage':False,'monthlyDecisionFrequency':True,'prices':'MOEX clean price + MOEX accrued interest','coupons':'MOEX bondization official coupon rows only'},'nextTask':'R0.5.8 Production Policy Decision / Evidence Review'}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"OFZ R0.5.7 COMMON-LIFE MOEX BACKTEST: PASS common={report['commonFrom']}..{report['commonTo']} days={len(common)} obs={len(dates)} y10={min(yields.values()):.2f}-{max(yields.values()):.2f}")
    print(f"BUY_HOLD terminal={hold['terminalValue']:.0f} dd={hold['maxDrawdown']:.4f} turnover={hold['turnoverPct']:.2f}")
    for x in comparisons:print(f"{x['name']}: delta={x['deltaTerminal']:.0f} ddImp={x['drawdownImprovement']:.4f} turnover={x['turnoverPct']:.2f}")

if __name__=='__main__':main()
