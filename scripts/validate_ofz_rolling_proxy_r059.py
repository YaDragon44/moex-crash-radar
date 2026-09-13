#!/usr/bin/env python3
from __future__ import annotations
import json, re, ssl
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

OUT=Path('web/ofz-radar/data/rolling-proxy-backtest.json')
UA='Mozilla/5.0 OFZ-Signal-Radar/0.5.9'
TERMS=[.25,.5,.75,1,2,3,5,7,10,15,20,30]
POLICIES={
 'BUY_HOLD':{'A':1,'B':1,'C':1,'D':1,'E':1},
 'BASELINE_100_60_25':{'A':1,'B':1,'C':1,'D':.60,'E':.25},
 'LATE_EXIT_100_80_50':{'A':1,'B':1,'C':1,'D':.80,'E':.50},
 'MILD_EXIT_100_90_65':{'A':1,'B':1,'C':1,'D':.90,'E':.65},
 'EARLY_CUT_100_85_60_25':{'A':1,'B':1,'C':.85,'D':.60,'E':.25},
}
START='2018-01-01'
END='2026-09-11'

class TableParser(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=[];self.in_cell=False
 def handle_starttag(self,t,a):
  if t=='tr':self.row=[]
  if t in ('td','th'):self.in_cell=True;self.cell=[]
 def handle_data(self,d):
  if self.in_cell:self.cell.append(d)
 def handle_endtag(self,t):
  if t in ('td','th') and self.in_cell:self.row.append(' '.join(''.join(self.cell).split()));self.in_cell=False
  if t=='tr' and self.row:self.rows.append(self.row)

def get(url,timeout=30):
 req=Request(url,headers={'User-Agent':UA,'Accept':'application/json,text/html,*/*'})
 with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:return r.read().decode('utf-8','replace')
def num(x):
 if x is None:return None
 try:return float(str(x).replace(',','.'))
 except Exception:
  m=re.search(r'-?\d+(?:[\.,]\d+)?',str(x));return float(m.group().replace(',','.')) if m else None
def rows(obj,name):
 b=obj.get(name) or {};c=b.get('columns') or [];return [dict(zip(c,r)) for r in (b.get('data') or [])]
def pick(r,*ks):
 for k in ks:
  if r.get(k) is not None:
   v=num(r.get(k))
   if v is not None:return v
 return None

def discover_universe():
 obj=json.loads(get('https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json?iss.meta=off&iss.only=securities'))
 out=[]
 for r in rows(obj,'securities'):
  sid=str(r.get('SECID') or '')
  name=str(r.get('SHORTNAME') or r.get('SECNAME') or '')
  mat=str(r.get('MATDATE') or '')[:10]
  cp=pick(r,'COUPONPERCENT');face=pick(r,'FACEVALUE') or 1000
  if not sid.startswith('SU262') or not re.match(r'^\d{4}-\d{2}-\d{2}$',mat):continue
  if cp is None or cp<=0:continue
  if datetime.strptime(mat,'%Y-%m-%d').date()<=datetime.strptime(START,'%Y-%m-%d').date()+timedelta(days=365*7):continue
  out.append({'secid':sid,'name':name,'matDate':mat,'couponPercent':cp,'faceValue':face})
 if len(out)<5:raise RuntimeError(f'fixed OFZ universe too small: {len(out)}')
 return out

def history(secid):
 out=[];start=0
 while True:
  u=f'https://iss.moex.com/iss/history/engines/stock/markets/bonds/boards/TQOB/securities/{secid}.json?iss.meta=off&iss.only=history&from={START}&till={END}&start={start}'
  obj=json.loads(get(u));rr=rows(obj,'history')
  if not rr:break
  for r in rr:
   ds=str(r.get('TRADEDATE') or '')[:10];clean=pick(r,'CLOSE','LEGALCLOSEPRICE','MARKETPRICE3','MARKETPRICE2','WAPRICE','MARKETPRICE','PREVPRICE');ai=pick(r,'ACCINT','ACCRUEDINT');face=pick(r,'FACEVALUE')
   if re.match(r'^\d{4}-\d{2}-\d{2}$',ds) and clean and clean>0 and ai is not None:out.append({'date':ds,'clean':clean,'ai':ai,'face':face})
  start+=len(rr)
  if len(rr)<100:break
  if start>5000:raise RuntimeError(secid+' pagination guard')
 return {x['date']:x for x in out}

def coupons(secid):
 obj=json.loads(get(f'https://iss.moex.com/iss/securities/{secid}/bondization.json?iss.meta=off&iss.only=coupons'))
 out=[]
 for r in rows(obj,'coupons'):
  ds=str(r.get('coupondate') or r.get('COUPONDATE') or '')[:10];v=pick(r,'value','VALUE','couponvalue','COUPONVALUE')
  if re.match(r'^\d{4}-\d{2}-\d{2}$',ds) and v is not None:out.append({'date':ds,'value':v})
 return out

def cbr_y10(ds):
 d=datetime.strptime(ds,'%Y-%m-%d').date()
 for _ in range(10):
  p=TableParser();p.feed(get(f'https://www.cbr.ru/eng/hd_base/zcyc_params/zcyc/?DateTo={d.strftime("%d.%m.%Y")}'))
  for r in p.rows:
   vv=[num(x) for x in r];vv=[x for x in vv if x is not None]
   if len(vv)>=12:
    ys=[float(x) for x in vv[-12:]]
    if all(0<x<60 for x in ys) and not all(abs(ys[i]-TERMS[i])<.001 for i in range(12)):return ys[8]
  d-=timedelta(days=1)
 raise RuntimeError('CBR 10Y unavailable '+ds)
def regime(y):return 'A' if y>=16 else 'B' if y>=14 else 'C' if y>=12 else 'D' if y>=10 else 'E'
def full(row,face):return face*row['clean']/100+row['ai']

def month_ends(all_dates):
 by={}
 for ds in sorted(all_dates):by[ds[:7]]=ds
 return sorted(by.values())

def choose_proxy(ds,universe,hmap):
 d=datetime.strptime(ds,'%Y-%m-%d').date();cand=[]
 for u in universe:
  if ds not in hmap.get(u['secid'],{}):continue
  mat=datetime.strptime(u['matDate'],'%Y-%m-%d').date();yrs=(mat-d).days/365.25
  if yrs<7:continue
  # duration proxy: prefer residual maturity around 12y, with >=7y floor.
  cand.append((abs(yrs-12),-yrs,u))
 return min(cand,key=lambda x:(x[0],x[1]))[2] if cand else None

def main():
 universe=discover_universe();hmap={};cmap={}
 for u in universe:
  h=history(u['secid'])
  if len(h)>=20:hmap[u['secid']]=h;cmap[u['secid']]=coupons(u['secid'])
 universe=[u for u in universe if u['secid'] in hmap]
 dates=month_ends(set().union(*(set(h.keys()) for h in hmap.values())))
 dates=[d for d in dates if START<=d<=END]
 selections=[]
 for ds in dates:
  u=choose_proxy(ds,universe,hmap)
  if u:selections.append({'date':ds,'secid':u['secid'],'matDate':u['matDate'],'faceValue':u['faceValue'],'fullPrice':full(hmap[u['secid']][ds],u['faceValue'])})
 if len(selections)<48:raise RuntimeError(f'proxy panel too short: {len(selections)} months')
 yields={x['date']:cbr_y10(x['date']) for x in selections}
 rc={}
 for y in yields.values():rc[regime(y)]=rc.get(regime(y),0)+1
 if not {'D','E'} & set(rc):raise RuntimeError(f'no D/E regimes in proxy panel: {rc}')

 def simulate(policy):
  capital=1_000_000.;cash=capital;qty=0;held=None;last=None;peak=capital;maxdd=0.;turn=0.;coupon_cash=0.;timeline=[]
  for sel in selections:
   ds=sel['date'];sid=sel['secid'];px=sel['fullPrice'];y=yields[ds];target=float(policy[regime(y)])
   if held and last:
    for cp in cmap.get(held,[]):
     if last<cp['date']<=ds:
      r=qty*cp['value'];cash+=r;coupon_cash+=r
   # If rolling proxy changes, sell old at its price on current date if available.
   if held and held!=sid and qty>0:
    old_u=next(u for u in universe if u['secid']==held)
    oldrow=hmap[held].get(ds)
    if oldrow:
     proceeds=qty*full(oldrow,old_u['faceValue']);cash+=proceeds;turn+=proceeds;qty=0
    else:
     # use latest available <= ds, but reject if stale >10 calendar days
     prev=[d for d in hmap[held] if d<=ds]
     if not prev:raise RuntimeError(f'no exit quote {held} {ds}')
     qd=max(prev)
     if (datetime.strptime(ds,'%Y-%m-%d')-datetime.strptime(qd,'%Y-%m-%d')).days>10:raise RuntimeError(f'stale exit quote {held} {qd}->{ds}')
     proceeds=qty*full(hmap[held][qd],old_u['faceValue']);cash+=proceeds;turn+=proceeds;qty=0
    held=sid
   if held is None:held=sid
   # mark current portfolio
   bond=qty*px;total=cash+bond;desired=total*target
   if bond>desired+px and qty>0:
    n=min(qty,int((bond-desired)//px));proceeds=n*px;qty-=n;cash+=proceeds;turn+=proceeds
   bond=qty*px;total=cash+bond;desired=total*target
   need=max(0.,desired-bond);n=int(min(cash,need)//px)
   if n>0:qty+=n;cash-=n*px;turn+=n*px
   value=cash+qty*px;peak=max(peak,value);maxdd=min(maxdd,value/peak-1)
   timeline.append({'date':ds,'secid':sid,'y10':y,'regime':regime(y),'targetExposure':target,'value':value})
   last=ds
  final=timeline[-1]['value']
  return {'terminalValue':final,'returnPct':final/capital-1,'maxDrawdown':maxdd,'turnoverPct':turn/capital,'couponCash':coupon_cash,'timeline':timeline}
 results={n:simulate(p) for n,p in POLICIES.items()};hold=results['BUY_HOLD'];comp=[]
 for n,r in results.items():
  if n=='BUY_HOLD':continue
  comp.append({'name':n,'deltaTerminal':r['terminalValue']-hold['terminalValue'],'drawdownImprovement':r['maxDrawdown']-hold['maxDrawdown'],'turnoverPct':r['turnoverPct']})
 report={'version':'0.5.9','status':'PASS','validationType':'DURATION_MATCHED_ROLLING_OFZ_REAL_PRICE_PROXY','dataSource':'MOEX ISS real quotes + MOEX official coupon rows + CBR 10Y','from':selections[0]['date'],'to':selections[-1]['date'],'monthlyObservations':len(selections),'regimeCounts':rc,'universeSize':len(universe),'selectedIssues':sorted(set(x['secid'] for x in selections)),'selectionRule':'At each month-end choose real fixed OFZ SU262 with residual maturity >=7y and closest to 12y; roll using real MOEX full prices.','results':results,'comparisons':comp,'bestReturnVsHold':max(comp,key=lambda x:x['deltaTerminal'])['name'],'bestDrawdownVsHold':max(comp,key=lambda x:x['drawdownImprovement'])['name'],'decision':'NO_PRODUCTION_CHANGE','reason':'Rolling proxy extends real-price evidence into D/E, but remains a proxy basket and requires robustness / leave-one-episode-out validation before production threshold change.','assumptions':{'taxes':False,'commissions':False,'slippage':False,'decisionFrequency':'monthly','durationMatching':'residual maturity proxy around 12 years; not exact modified duration'},'nextTask':'R0.5.10 Rolling Proxy Robustness / Leave-One-Episode-Out'}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f"OFZ R0.5.9 ROLLING PROXY: PASS {report['from']}..{report['to']} obs={len(selections)} regimes={rc} universe={len(universe)} issues={len(report['selectedIssues'])}")
 print('BUY_HOLD',hold['terminalValue'],hold['maxDrawdown'],hold['turnoverPct'])
 for x in comp:print(x)

if __name__=='__main__':main()
