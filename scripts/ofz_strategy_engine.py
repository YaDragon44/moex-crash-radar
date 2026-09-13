from __future__ import annotations
from datetime import timedelta
from math import floor
from ofz_cashflow_engine import _date,_ds,_add_years,coupon_amount,schedule_integrity,theoretical_full_price,WEIGHTS

DEFAULT_PATH=[16.2,15.0,13.0,11.0,9.0,5.0]

def regime(y):
    return 'A' if y>=16 else 'B' if y>=14 else 'C' if y>=12 else 'D' if y>=10 else 'E'

def exposure_for_yield(y):
    return 1.0 if y>=12 else .60 if y>=10 else .25

def _interpolate(path,start,ds):
    d=_date(ds);years=(d-start).days/365.0
    if years<=0:return float(path[0])
    if years>=len(path)-1:return float(path[-1])
    i=int(years);f=years-i
    return float(path[i])+(float(path[i+1])-float(path[i]))*f

def simulate_path_strategy(portfolio,bonds,valuation_date,path=None,active=True,weights=WEIGHTS):
    path=list(path or DEFAULT_PATH)
    if not portfolio.get('ready') or len(path)<2:return {'ready':False,'reason':'portfolio/path not ready'}
    start=_date(valuation_date);horizon=_add_years(start,len(path)-1) if start else None
    if not start or not horizon:return {'ready':False,'reason':'invalid valuation date'}
    mp={str(b['secid']):b for b in bonds};qty={p['secid']:int(p['qty']) for p in portfolio['positions']};cash=float(portfolio.get('cash') or 0);initial=float(portfolio['capital'])
    coupon_events={}
    for p in portfolio['positions']:
        for r in schedule_integrity(mp[p['secid']],valuation_date,_ds(horizon))['extended']:
            coupon_events.setdefault(r['date'],[]).append({'secid':p['secid'],'value':r.get('value')})
    rebalance_dates={_ds(_add_years(start,i)):float(y) for i,y in enumerate(path)}
    dates=sorted(set(coupon_events)|set(rebalance_dates))
    actions=[];total_coupons=0.0;realized_sales=0.0;reinvested=0.0;turnover=0.0;peak=initial;max_dd=0.0
    def mark(ds,y):
        values={};bond_value=0.0
        for secid,q in qty.items():
            fp=theoretical_full_price(mp[secid],y,ds)
            if fp is None:return None
            v=q*fp;values[secid]={'fp':fp,'value':v};bond_value+=v
        total=bond_value+cash
        return {'values':values,'bondValue':bond_value,'total':total}
    def target_exposure(y):return exposure_for_yield(y) if active else 1.0
    def sell_to_target(ds,y,mv,target):
        nonlocal cash,realized_sales,turnover
        desired=mv['total']*target
        if mv['bondValue']<=desired+1:return
        ratio=max(0.0,min(1.0,(mv['bondValue']-desired)/mv['bondValue']))
        sold=0.0
        for secid in list(qty):
            q=qty[secid];lot=max(1,int(mp[secid].get('lotSize') or 1));sell_qty=floor((q*ratio)/lot)*lot
            if sell_qty<=0:continue
            proceeds=sell_qty*mv['values'][secid]['fp'];qty[secid]-=sell_qty;cash+=proceeds;sold+=proceeds
        realized_sales+=sold;turnover+=sold
        if sold>0:actions.append({'date':ds,'yield':y,'regime':regime(y),'action':'REDUCE' if target>.25 else 'ROTATE','targetExposure':target,'amount':sold})
    def buy_to_target(ds,y,mv,target):
        nonlocal cash,reinvested,turnover
        desired=mv['total']*target;need=max(0.0,desired-mv['bondValue']);budget=min(cash,need)
        if budget<=0:return
        spent=0.0
        for _ in range(5000):
            pick=None;best=-1e100
            current=mark(ds,y)
            if not current:break
            for secid,w in weights.items():
                row=current['values'][secid];target_v=current['total']*target*w;deficit=target_v-row['value'];lot=max(1,int(mp[secid].get('lotSize') or 1));cost=row['fp']*lot
                if cost<=budget-spent and deficit>best:best=deficit;pick=(secid,lot,cost)
            if not pick:break
            secid,lot,cost=pick;qty[secid]+=lot;cash-=cost;spent+=cost
        reinvested+=spent;turnover+=spent
    timeline=[]
    for ds in dates:
        if _date(ds)<=start:continue
        y=_interpolate(path,start,ds)
        for ev in coupon_events.get(ds,[]):
            c=float(ev['value']) if ev.get('value') is not None else coupon_amount(mp[ev['secid']])
            if c is not None:
                received=qty[ev['secid']]*c;cash+=received;total_coupons+=received
        mv=mark(ds,y)
        if not mv:return {'ready':False,'reason':f'pricing unavailable {ds}'}
        target=target_exposure(y)
        sell_to_target(ds,y,mv,target)
        mv=mark(ds,y)
        buy_to_target(ds,y,mv,target)
        mv=mark(ds,y)
        peak=max(peak,mv['total']);dd=mv['total']/peak-1;max_dd=min(max_dd,dd)
        if ds in rebalance_dates:
            timeline.append({'date':ds,'yield':y,'regime':regime(y),'targetExposure':target,'value':mv['total'],'cash':cash,'bondValue':mv['bondValue']})
    final=mark(_ds(horizon),float(path[-1]))
    if not final:return {'ready':False,'reason':'final pricing unavailable'}
    years=len(path)-1;cagr=(final['total']/initial)**(1/years)-1
    return {'ready':True,'mode':'ACTIVE' if active else 'BUY_HOLD','path':path,'horizonDate':_ds(horizon),'terminalValue':final['total'],'returnPct':final['total']/initial-1,'cagr':cagr,'cash':cash,'bondValue':final['bondValue'],'totalCoupons':total_coupons,'reinvested':reinvested,'realizedSales':realized_sales,'turnover':turnover,'turnoverPct':turnover/initial,'maxDrawdown':max_dd,'actions':actions,'timeline':timeline,'economicSanity':-.20<cagr<.35}

def compare_strategies(portfolio,bonds,valuation_date,path=None):
    path=list(path or DEFAULT_PATH);hold=simulate_path_strategy(portfolio,bonds,valuation_date,path,False);active=simulate_path_strategy(portfolio,bonds,valuation_date,path,True)
    ready=hold.get('ready') and active.get('ready') and hold.get('economicSanity') and active.get('economicSanity')
    return {'ready':bool(ready),'path':path,'buyHold':hold,'active':active,'deltaTerminal':active.get('terminalValue',0)-hold.get('terminalValue',0) if ready else None,'deltaCagr':active.get('cagr',0)-hold.get('cagr',0) if ready else None,'assumptions':{'protectiveSleeveYield':0.0,'taxes':False,'commissions':False,'slippage':False,'rebalanceRule':'continuous exposure gate evaluated at coupon/rebalance events'}}
