#!/usr/bin/env python3
import json, re, ssl
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from ofz_cashflow_engine import build_portfolio, quality_gate, scenario_now, simulate_reinvestment, schedule_integrity

OUT=Path('web/ofz-radar/data/current.json')
UA='Mozilla/5.0 OFZ-Signal-Radar/0.5.2'
SECIDS={'26254':'SU26254RMFS1','26253':'SU26253RMFS3','26247':'SU26247RMFS5','26248':'SU26248RMFS3'}

class TableParser(HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]; self.row=[]; self.cell=[]; self.in_cell=False
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        if tag in ('td','th'): self.in_cell=True; self.cell=[]
    def handle_data(self,data):
        if self.in_cell: self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.in_cell:
            self.row.append(' '.join(''.join(self.cell).split())); self.in_cell=False
        if tag=='tr' and self.row:self.rows.append(self.row)

def get(url,timeout=25):
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/html,*/*'})
    with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:return r.read().decode('utf-8','replace')

def num(s):
    if s is None:return None
    m=re.search(r'-?\d+(?:\.\d+)?',str(s).replace('\xa0',' ').replace(' ','').replace(',','.'))
    return float(m.group()) if m else None

def tables(url):p=TableParser();p.feed(get(url));return p.rows

def last_workday(d):
    while d.weekday()>=5:d-=timedelta(days=1)
    return d

def fetch_curve(now):
    d=last_workday(now.date());terms=[.25,.5,.75,1,2,3,5,7,10,15,20,30]
    for _ in range(8):
        ds=d.strftime('%d.%m.%Y');candidates=[]
        for row in tables(f'https://www.cbr.ru/hd_base/zcyc_params/zcyc/?DateTo={ds}'):
            vals=[num(x) for x in row];vals=[x for x in vals if x is not None]
            if len(vals)>=12:candidates.append(vals[-12:])
        if len(candidates)>=2:
            ys=next((v for v in candidates if all(0<x<50 for x in v) and not all(abs(v[i]-terms[i])<.01 for i in range(12))),None)
            if ys:return {'date':ds,'points':[{'years':t,'label':('%gY'%t),'yield':round(y,4)} for t,y in zip(terms,ys)],'source':'CBR'}
        d=last_workday(d-timedelta(days=1))
    raise RuntimeError('CBR curve unavailable')

def fetch_key_rate():
    for r in tables('https://www.cbr.ru/hd_base/KeyRate/?UniDbQuery.Posted=True'):
        if len(r)>=2 and re.match(r'\d{2}\.\d{2}\.\d{4}',r[0]):
            v=num(r[1])
            if v is not None:return {'date':r[0],'value':v,'source':'CBR'}
    return {'date':None,'value':None,'source':'CBR:N/A'}

def fetch_inflation():
    for r in tables('https://www.cbr.ru/statistics/ddkp/infl/'):
        if len(r)>=4 and re.match(r'\d{2}\.\d{4}',r[0]):
            vals=[num(x) for x in r[1:4]]
            if all(v is not None for v in vals):return {'date':r[0],'keyRate':vals[0],'yoy':vals[1],'target':vals[2],'source':'CBR'}
    return {'date':None,'yoy':None,'target':4.0,'source':'CBR:N/A'}

def moex_block(obj,name):
    b=obj.get(name) or {};cols=b.get('columns') or [];data=b.get('data') or []
    return dict(zip(cols,data[0])) if data else {}

def moex_rows(obj,name):
    b=obj.get(name) or {};cols=b.get('columns') or []
    return [dict(zip(cols,row)) for row in (b.get('data') or [])]

def fetch_bondization(secid):
    try:o=json.loads(get(f'https://iss.moex.com/iss/securities/{secid}/bondization.json?iss.meta=off&iss.only=coupons'))
    except Exception:return []
    out={}
    for x in moex_rows(o,'coupons'):
        d=x.get('coupondate') or x.get('COUPONDATE') or x.get('couponDate') or x.get('date') or x.get('DATE')
        if not re.match(r'^\d{4}-\d{2}-\d{2}$',str(d)):continue
        raw=x.get('value') if x.get('value') is not None else x.get('VALUE') if x.get('VALUE') is not None else x.get('couponvalue') if x.get('couponvalue') is not None else x.get('COUPONVALUE')
        out[str(d)]={'date':str(d),'value':num(raw)}
    return [out[k] for k in sorted(out)]

def fetch_bond(label,secid):
    u=f'https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities/{secid}.json?iss.meta=off&iss.only=securities,marketdata'
    o=json.loads(get(u));s=moex_block(o,'securities');m=moex_block(o,'marketdata')
    price=m.get('LAST') or m.get('MARKETPRICE') or m.get('LCURRENTPRICE') or s.get('PREVPRICE');ytm=m.get('YIELD') or m.get('EFFECTIVEYIELD');schedule=fetch_bondization(secid)
    return {'secid':label,'moexSecid':secid,'price':num(price),'ytm':num(ytm),'couponPercent':num(s.get('COUPONPERCENT')),'couponValue':num(s.get('COUPONVALUE')),'couponPeriod':num(s.get('COUPONPERIOD')) or 182,'nextCouponDate':s.get('NEXTCOUPON'),'couponSchedule':schedule,'scheduleSource':'MOEX_BONDIZATION' if schedule else 'SYNTHETIC_FALLBACK','faceValue':num(s.get('FACEVALUE')) or 1000,'lotSize':int(num(s.get('LOTSIZE')) or 1),'accruedInt':num(s.get('ACCRUEDINT')) or 0,'duration':num(m.get('DURATION')),'matDate':s.get('MATDATE'),'quality':'LIVE' if m.get('LAST') is not None else 'DELAYED','source':'MOEX'}

def regime(y):return None if y is None else 'A' if y>=16 else 'B' if y>=14 else 'C' if y>=12 else 'D' if y>=10 else 'E'
def signal_for(r):return {'A':'ДОКУПИТЬ ДЛИННЫЕ ФИКСЫ','B':'ДОКУПИТЬ / ДЕРЖАТЬ','C':'ДЕРЖАТЬ','D':'ДЕРЖАТЬ / СОКРАТИТЬ','E':'РОТИРОВАТЬ В КОРОТКИЕ / ФЛОАТЕРЫ'}.get(r,'НАБЛЮДАТЬ')
def iso_curve_date(s):return datetime.strptime(s,'%d.%m.%Y').date().isoformat()

def main():
    now=datetime.now(timezone.utc);curve=fetch_curve(now);kr=fetch_key_rate();inf=fetch_inflation();valuation_date=iso_curve_date(curve['date']);bonds=[fetch_bond(k,v) for k,v in SECIDS.items()]
    for b in bonds:
        si=schedule_integrity(b,valuation_date);b['scheduleStatus']=si['status'];b['scheduleSource']='MOEX_FULL_SCHEDULE' if si['status']=='FULL' else 'MOEX_PARTIAL_EXTENDED' if si['status']=='PARTIAL_EXTENDED' else 'SYNTHETIC_FALLBACK' if si['status']=='SYNTHETIC' else 'INVALID'
    y10=next((p['yield'] for p in curve['points'] if p['years']==10),None);raw=regime(y10);known=1 if inf.get('yoy') is not None else 0;blocked=raw in ('A','B','D','E') and known<2
    confirmed={'id':raw,'signal':signal_for(raw) if not blocked else 'НАБЛЮДАТЬ','blocked':blocked,'blockReason':'недостаточно подтвержденных макрофакторов' if blocked else None,'confidence':'LOW' if known<2 else 'MEDIUM','macroScore':None}
    portfolio=build_portfolio(bonds,valuation_date);pq=quality_gate(bonds,valuation_date);scenario_yields=[14,12,10,8,5]
    scenarios=[{'targetYield':y,'repricedNow':scenario_now(portfolio,bonds,y,valuation_date),'fiveYear':simulate_reinvestment(portfolio,bonds,y,valuation_date,5)} for y in scenario_yields] if portfolio.get('ready') and pq.get('ok') else []
    sanity=all(x['fiveYear'].get('ready') and x['fiveYear'].get('economicSanity') for x in scenarios) if scenarios else False
    snap={'version':'0.5.2','fetchedAt':now.isoformat(),'valuationDate':valuation_date,'curve':curve,'curveHistory':[],'keyRate':kr,'inflation':inf,'inflationExpectations':None,'minfinAuction':None,'budget':None,'cbTone':None,'bonds':bonds,'portfolio':portfolio,'portfolioQuality':{**pq,'economicSanity':sanity},'portfolioScenarios':scenarios,'rawRegime':raw,'confirmedRegime':confirmed,'transition':{'text':'LIVE SNAPSHOT'},'macro':{'known':known},'quality':{'market':'LIVE' if all(b['quality'] in ('LIVE','DELAYED') for b in bonds) else 'STALE','curve':'LIVE','macro':'PARTIAL','system':'LIVE' if pq.get('ok') and sanity else 'DEGRADED'},'sources':{'inflationExpectations':'N/A','minfinAuctions':'N/A','budget':'N/A','cbTone':'N/A','curve':'CBR','bonds':'MOEX','cashflows':'MOEX Bondization + safe synthetic extension'}}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"OFZ SNAPSHOT PASS version=0.5.2 date={curve['date']} y10={y10} regime={raw} bonds={len(bonds)} scenarios={len(scenarios)} sanity={sanity}")
if __name__=='__main__':main()
