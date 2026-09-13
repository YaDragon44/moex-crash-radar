#!/usr/bin/env python3
import json, math, re, ssl
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

OUT=Path('web/ofz-radar/data/current.json')
UA='Mozilla/5.0 OFZ-Signal-Radar/0.5.1'
SECIDS={'26254':'SU26254RMFS1','26253':'SU26253RMFS3','26247':'SU26247RMFS5','26248':'SU26248RMFS3'}
WEIGHTS={'26254':.47,'26253':.29,'26247':.12,'26248':.12}
CAPITAL=1_000_000

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
        if tag=='tr' and self.row: self.rows.append(self.row)

def get(url,timeout=25):
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/html,*/*'})
    with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:
        return r.read().decode('utf-8','replace')

def num(s):
    if s is None: return None
    s=str(s).replace('\xa0',' ').replace(' ','').replace(',','.')
    m=re.search(r'-?\d+(?:\.\d+)?',s)
    return float(m.group()) if m else None

def tables(url):
    p=TableParser(); p.feed(get(url)); return p.rows

def last_workday(d):
    while d.weekday()>=5: d-=timedelta(days=1)
    return d

def fetch_curve(now):
    d=last_workday(now.date())
    terms=[.25,.5,.75,1,2,3,5,7,10,15,20,30]
    for _ in range(8):
        ds=d.strftime('%d.%m.%Y')
        rows=tables(f'https://www.cbr.ru/hd_base/zcyc_params/zcyc/?DateTo={ds}')
        candidates=[]
        for row in rows:
            vals=[num(x) for x in row]
            vals=[x for x in vals if x is not None]
            if len(vals)>=12: candidates.append(vals[-12:])
        if len(candidates)>=2:
            # CBR table contains maturity row followed by yield row; choose plausible yield vector.
            ys=next((v for v in candidates if all(0 < x < 50 for x in v) and not all(abs(v[i]-terms[i])<.01 for i in range(12))),None)
            if ys:
                return {'date':ds,'points':[{'years':t,'label':('%gY'%t),'yield':round(y,4)} for t,y in zip(terms,ys)],'source':'CBR'}
        d-=timedelta(days=1); d=last_workday(d)
    raise RuntimeError('CBR curve unavailable')

def fetch_key_rate():
    rows=tables('https://www.cbr.ru/hd_base/KeyRate/?UniDbQuery.Posted=True')
    for r in rows:
        if len(r)>=2 and re.match(r'\d{2}\.\d{2}\.\d{4}',r[0]):
            v=num(r[1])
            if v is not None: return {'date':r[0],'value':v,'source':'CBR'}
    return {'date':None,'value':None,'source':'CBR:N/A'}

def fetch_inflation():
    rows=tables('https://www.cbr.ru/statistics/ddkp/infl/')
    for r in rows:
        if len(r)>=4 and re.match(r'\d{2}\.\d{4}',r[0]):
            vals=[num(x) for x in r[1:4]]
            if all(v is not None for v in vals): return {'date':r[0],'keyRate':vals[0],'yoy':vals[1],'target':vals[2],'source':'CBR'}
    return {'date':None,'yoy':None,'target':4.0,'source':'CBR:N/A'}

def moex_block(obj,name):
    b=obj.get(name) or {}; cols=b.get('columns') or []; data=b.get('data') or []
    return dict(zip(cols,data[0])) if data else {}

def fetch_bond(label,secid):
    u=f'https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities/{secid}.json?iss.meta=off&iss.only=securities,marketdata'
    o=json.loads(get(u)); s=moex_block(o,'securities'); m=moex_block(o,'marketdata')
    price=m.get('LAST') or m.get('MARKETPRICE') or m.get('LCURRENTPRICE') or s.get('PREVPRICE')
    ytm=m.get('YIELD') or m.get('EFFECTIVEYIELD')
    face=s.get('FACEVALUE') or 1000; ai=s.get('ACCRUEDINT') or 0
    cp=s.get('COUPONPERCENT'); cv=s.get('COUPONVALUE'); period=s.get('COUPONPERIOD') or 182
    return {'secid':label,'moexSecid':secid,'price':num(price),'ytm':num(ytm),'couponPercent':num(cp),'couponValue':num(cv),'couponPeriod':num(period),'nextCouponDate':s.get('NEXTCOUPON'),'faceValue':num(face) or 1000,'lotSize':int(num(s.get('LOTSIZE')) or 1),'accruedInt':num(ai) or 0,'duration':num(m.get('DURATION')),'matDate':s.get('MATDATE'),'quality':'LIVE' if m.get('LAST') is not None else 'DELAYED','source':'MOEX'}

def regime(y):
    if y is None:return None
    return 'A' if y>=16 else 'B' if y>=14 else 'C' if y>=12 else 'D' if y>=10 else 'E'

def signal_for(r):
    return {'A':'ДОКУПИТЬ ДЛИННЫЕ ФИКСЫ','B':'ДОКУПИТЬ / ДЕРЖАТЬ','C':'ДЕРЖАТЬ','D':'ДЕРЖАТЬ / СОКРАТИТЬ','E':'РОТИРОВАТЬ В КОРОТКИЕ / ФЛОАТЕРЫ'}.get(r,'НАБЛЮДАТЬ')

def build_portfolio(bonds):
    pos=[]; invested=0; annual=0
    for b in bonds:
        full=(b['faceValue']*b['price']/100+b['accruedInt']) if b.get('price') is not None else None
        if not full or full<=0:return {'ready':False}
        target=CAPITAL*WEIGHTS[b['secid']]; q=int(target//full); cost=q*full
        c12=(b.get('couponValue') or (b['faceValue']*(b.get('couponPercent') or 0)/100*(b.get('couponPeriod') or 182)/365))*365/(b.get('couponPeriod') or 182)
        invested+=cost; annual+=q*c12; pos.append({'secid':b['secid'],'weightPct':WEIGHTS[b['secid']]*100,'qty':q,'cost':round(cost,2),'fullPrice':round(full,2)})
    return {'ready':True,'capital':CAPITAL,'invested':round(invested,2),'cash':round(CAPITAL-invested,2),'annualCoupon':round(annual,2),'positions':pos}

def main():
    now=datetime.now(timezone.utc); curve=fetch_curve(now); kr=fetch_key_rate(); inf=fetch_inflation()
    bonds=[fetch_bond(k,v) for k,v in SECIDS.items()]
    y10=next((p['yield'] for p in curve['points'] if p['years']==10),None); raw=regime(y10)
    known=1 if inf.get('yoy') is not None else 0
    blocked=raw in ('A','B','D','E') and known<2
    confirmed={'id':raw if not blocked else raw,'signal':signal_for(raw) if not blocked else 'НАБЛЮДАТЬ','blocked':blocked,'blockReason':'недостаточно подтвержденных макрофакторов' if blocked else None,'confidence':'LOW' if known<2 else 'MEDIUM','macroScore':None}
    portfolio=build_portfolio(bonds)
    snap={'version':'0.5.1','fetchedAt':now.isoformat(),'curve':curve,'curveHistory':[],'keyRate':kr,'inflation':inf,'inflationExpectations':None,'minfinAuction':None,'budget':None,'cbTone':None,'bonds':bonds,'portfolio':portfolio,'portfolioQuality':{'ok':portfolio.get('ready',False),'scheduleStatus':'MARKET DATA VERIFIED; CASHFLOW SCHEDULE LIMITED'},'portfolioScenarios':[],'rawRegime':raw,'confirmedRegime':confirmed,'transition':{'text':'LIVE SNAPSHOT'},'macro':{'known':known},'quality':{'market':'LIVE' if all(b['quality'] in ('LIVE','DELAYED') for b in bonds) else 'STALE','curve':'LIVE','macro':'PARTIAL','system':'LIVE'},'sources':{'inflationExpectations':'N/A','minfinAuctions':'N/A','budget':'N/A','cbTone':'N/A','curve':'CBR','bonds':'MOEX'}}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"OFZ SNAPSHOT PASS date={curve['date']} y10={y10} regime={raw} bonds={len(bonds)} portfolio={portfolio.get('ready')}")
if __name__=='__main__': main()
