from __future__ import annotations
from datetime import datetime, timedelta
from math import floor, isfinite

WEIGHTS={'26254':.47,'26253':.29,'26247':.12,'26248':.12}
CAPITAL=1_000_000

def _date(v):
    if not v:return None
    try:return datetime.strptime(str(v)[:10],'%Y-%m-%d').date()
    except ValueError:return None

def _ds(d):return d.isoformat() if d else None

def full_price(b):
    try:
        face=float(b['faceValue']);clean=float(b['price']);ai=float(b.get('accruedInt') or 0)
        return face*clean/100+ai if face>0 and clean>0 and ai>=0 else None
    except (TypeError,ValueError,KeyError):return None

def coupon_amount(b):
    try:
        if b.get('couponValue') is not None and float(b['couponValue'])>=0:return float(b['couponValue'])
        face=float(b['faceValue']);rate=float(b['couponPercent']);period=float(b['couponPeriod'])
        return face*rate/100*period/365 if face>0 and rate>=0 and period>0 else None
    except (TypeError,ValueError,KeyError):return None

def _schedule(b):
    rows=[]
    for x in b.get('couponSchedule') or []:
        r={'date':x,'value':None} if isinstance(x,str) else {'date':x.get('date'),'value':x.get('value')}
        if _date(r['date']):rows.append(r)
    ded={r['date']:r for r in rows}
    return [ded[k] for k in sorted(ded)]

def schedule_integrity(b,valuation_date,horizon_date=None):
    val=_date(valuation_date);mat=_date(b.get('matDate'));period=float(b.get('couponPeriod') or 0);h=_date(horizon_date)
    limit=min(mat,h) if mat and h else mat
    if not val or not mat or not limit or period<=0:return {'status':'INVALID','complete':False,'official':[],'extended':[]}
    official=[r.copy() for r in _schedule(b) if val<_date(r['date'])<=limit]
    tol=max(7,int(period*.20+0.999));gaps_ok=all(abs((_date(official[i]['date'])-_date(official[i-1]['date'])).days-period)<=tol for i in range(1,len(official)))
    extended=list(official);anchor=_date(official[-1]['date']) if official else _date(b.get('nextCouponDate'))
    while anchor and anchor<=val:anchor+=timedelta(days=period)
    if not official and anchor and anchor<=limit:extended.append({'date':_ds(anchor),'value':None,'synthetic':True})
    guard=0
    while anchor and anchor<limit and guard<600:
        guard+=1;nxt=anchor+timedelta(days=period)
        if nxt>limit:break
        ds=_ds(nxt)
        if not any(r['date']==ds for r in extended):extended.append({'date':ds,'value':None,'synthetic':True})
        anchor=nxt
    extended.sort(key=lambda r:r['date']);last=_date(official[-1]['date']) if official else None;remaining=(limit-last).days if last else 10**9
    complete=bool(official) and gaps_ok and remaining<=period+tol
    status='FULL' if complete else 'PARTIAL_EXTENDED' if official else 'SYNTHETIC' if extended else 'INVALID'
    return {'status':status,'complete':complete,'gapsOk':gaps_ok,'official':official,'extended':extended,'limitDate':_ds(limit)}

def coupon_cashflow_12m(b,valuation_date):
    val=_date(valuation_date)
    if not val:return None
    info=schedule_integrity(b,valuation_date,_ds(val+timedelta(days=365)));fallback=coupon_amount(b);amount=0;count=0;verified=0
    for r in info['extended']:
        v=float(r['value']) if r.get('value') is not None else fallback
        if v is None:return None
        amount+=v;count+=1;verified+=1 if r.get('value') is not None else 0
    return {'amount':amount,'count':count,'verified':verified,'status':info['status']}

def build_portfolio(bonds,valuation_date,capital=CAPITAL,weights=WEIGHTS):
    mp={str(b['secid']):b for b in bonds};pos=[];cash=float(capital);invested=0;annual=0
    for secid,w in weights.items():
        b=mp.get(secid);fp=full_price(b) if b else None
        if not b or not fp:return {'ready':False,'capital':capital,'positions':[],'cash':capital,'invested':0,'reason':f'missing portfolio data {secid}'}
        lot=max(1,int(b.get('lotSize') or 1));qty=floor((capital*w)/(fp*lot))*lot;cost=qty*fp;flow=coupon_cashflow_12m(b,valuation_date)
        annual+=qty*(flow['amount'] if flow else b['faceValue']*(b.get('couponPercent') or 0)/100)
        pos.append({'secid':secid,'weightPct':w*100,'weight':w,'qty':qty,'lotSize':lot,'cost':round(cost,2),'fullPrice':round(fp,2),'ytm':b.get('ytm')});cash-=cost;invested+=cost
    return {'ready':True,'capital':capital,'invested':round(invested,2),'cash':round(cash,2),'annualCoupon':round(annual,2),'annualCouponYield':annual/invested if invested else None,'positions':pos}

def theoretical_full_price(b,target_yield,valuation_date):
    val=_date(valuation_date);mat=_date(b.get('matDate'));c=coupon_amount(b)
    try:y=float(target_yield);face=float(b['faceValue']);period=float(b['couponPeriod'])
    except (TypeError,ValueError,KeyError):return None
    if not val or not mat or val>=mat or y<0 or face<=0 or period<=0 or c is None:return None
    info=schedule_integrity(b,valuation_date)
    if not info['extended']:return None
    freq=365/period;pr=(y/100)/freq;pv=0.0
    for r in info['extended']:
        d=_date(r['date']);n=((d-val).days/365)*freq;cv=float(r['value']) if r.get('value') is not None else c;pv+=cv/((1+pr)**n)
    nm=((mat-val).days/365)*freq;pv+=face/((1+pr)**nm)
    return pv if isfinite(pv) else None

def scenario_now(portfolio,bonds,target_yield,valuation_date):
    if not portfolio.get('ready'):return {'ready':False,'targetYield':target_yield,'value':None}
    mp={str(b['secid']):b for b in bonds};value=float(portfolio.get('cash') or 0);positions=[]
    for p in portfolio['positions']:
        fp=theoretical_full_price(mp[p['secid']],target_yield,valuation_date)
        if fp is None:return {'ready':False,'targetYield':target_yield,'value':None,'reason':f"scenario data {p['secid']}"}
        v=p['qty']*fp;value+=v;positions.append({'secid':p['secid'],'qty':p['qty'],'fullPrice':fp,'value':v})
    return {'ready':True,'targetYield':target_yield,'value':value,'returnPct':value/portfolio['capital']-1,'positions':positions,'cash':portfolio.get('cash',0)}

def _add_years(d,n):
    try:return d.replace(year=d.year+n)
    except ValueError:return d.replace(month=2,day=28,year=d.year+n)

def simulate_reinvestment(portfolio,bonds,target_yield,valuation_date,horizon_years=5,weights=WEIGHTS):
    if not portfolio.get('ready'):return {'ready':False,'targetYield':target_yield,'reason':'portfolio not ready'}
    start=_date(valuation_date);horizon=_add_years(start,horizon_years) if start else None
    if not start or not horizon:return {'ready':False,'targetYield':target_yield,'reason':'invalid valuation date'}
    mp={str(b['secid']):b for b in bonds};qty={p['secid']:p['qty'] for p in portfolio['positions']};cash=float(portfolio.get('cash') or 0);total_coupons=0;reinvested=0;purchases=0;events={}
    for p in portfolio['positions']:
        for r in schedule_integrity(mp[p['secid']],valuation_date,_ds(horizon))['extended']:events.setdefault(r['date'],[]).append({'secid':p['secid'],'value':r.get('value')})
    current=sum(float(mp[p['secid']].get('ytm') or target_yield)*p['weight'] for p in portfolio['positions'])
    def yield_at(ds):
        t=(_date(ds)-start).days/max(1,(horizon-start).days);return current+(float(target_yield)-current)*max(0,min(1,t))
    def market_values(ds,y):
        out={};total=cash
        for p in portfolio['positions']:
            fp=theoretical_full_price(mp[p['secid']],y,ds)
            if fp is None:return None
            out[p['secid']]={'fp':fp,'value':qty[p['secid']]*fp};total+=out[p['secid']]['value']
        return {'out':out,'total':total}
    for ds in sorted(events):
        for ev in events[ds]:
            c=float(ev['value']) if ev.get('value') is not None else coupon_amount(mp[ev['secid']])
            if c is None:continue
            received=qty[ev['secid']]*c;cash+=received;total_coupons+=received
        mv=market_values(ds,yield_at(ds))
        if not mv:continue
        for _ in range(5000):
            pick=None;best=-1e100
            for p in portfolio['positions']:
                row=mv['out'][p['secid']];target=mv['total']*weights.get(p['secid'],p['weight']);deficit=target-row['value'];lot=max(1,int(mp[p['secid']].get('lotSize') or 1));lot_cost=row['fp']*lot
                if lot_cost<=cash and deficit>best:best=deficit;pick=(p,row,lot,lot_cost)
            if not pick:break
            p,row,lot,lot_cost=pick;qty[p['secid']]+=lot;cash-=lot_cost;reinvested+=lot_cost;purchases+=lot;row['value']+=lot_cost
    final=market_values(_ds(horizon),float(target_yield))
    if not final:return {'ready':False,'targetYield':target_yield,'reason':'final pricing unavailable'}
    cagr=(final['total']/portfolio['capital'])**(1/horizon_years)-1
    return {'ready':True,'targetYield':target_yield,'horizonDate':_ds(horizon),'terminalValue':final['total'],'finalValue':final['total'],'cash':cash,'totalCoupons':total_coupons,'reinvested':reinvested,'purchases':purchases,'returnPct':final['total']/portfolio['capital']-1,'cagr':cagr,'economicSanity':-.20<cagr<.35,'positions':[{'secid':s,'qty':q,'value':final['out'][s]['value'],'fullPrice':final['out'][s]['fp']} for s,q in qty.items()]}

def quality_gate(bonds,valuation_date):
    issues=[];warnings=[];statuses=[]
    for b in bonds:
        sid=str(b.get('secid','?'))
        if b.get('quality') not in ('LIVE','DELAYED'):issues.append(f'{sid}: quote {b.get("quality")}')
        if full_price(b) is None:issues.append(f'{sid}: full price N/A')
        if coupon_amount(b) is None:issues.append(f'{sid}: coupon N/A')
        si=schedule_integrity(b,valuation_date);statuses.append(si['status'])
        if si['status']=='INVALID':issues.append(f'{sid}: coupon schedule invalid')
        elif si['status']!='FULL':warnings.append(f'{sid}: {si["status"]}')
    if all(s=='FULL' for s in statuses):ss='MOEX VERIFIED'
    elif all(s in ('FULL','PARTIAL_EXTENDED') for s in statuses):ss='MOEX VERIFIED + SAFE EXTENSION'
    elif any(s=='INVALID' for s in statuses):ss='INVALID'
    else:ss='PARTIAL / SYNTHETIC'
    return {'ok':not issues,'ready':not issues,'issues':issues,'warnings':warnings,'scheduleStatus':ss}
