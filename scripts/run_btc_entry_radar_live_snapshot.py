from __future__ import annotations
import json, math, statistics
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from scripts.btc_entry_radar_r1_4_0 import EntryRadarInput, to_dict
FGI_URL='https://api.alternative.me/fng/'
OKX_CANDLES='https://www.okx.com/api/v5/market/candles'
OKX_OI_HISTORY='https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history'

def fetch_json(url,params):
    req=Request(f"{url}?{urlencode(params)}",headers={'User-Agent':'btc-entry-radar/1.4.4'})
    with urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

def percentile(values,q):
    x=sorted(values); pos=(len(x)-1)*q; lo,hi=math.floor(pos),math.ceil(pos)
    return x[lo] if lo==hi else x[lo]*(hi-pos)+x[hi]*(pos-lo)

def load_fgi(now):
    row=fetch_json(FGI_URL,{'limit':2,'format':'json'})['data'][0]; ts=datetime.fromtimestamp(int(row['timestamp']),tz=timezone.utc); age=(now-ts).total_seconds()/3600
    return {'value':float(row['value']),'classification':row.get('value_classification'),'timestamp':ts.isoformat(),'age_h':age,'fresh':age<=48}

def load_candles(now):
    p=fetch_json(OKX_CANDLES,{'instId':'BTC-USDT','bar':'4H','limit':60})
    if p.get('code')!='0':raise RuntimeError(p.get('msg'))
    rows=[{'ts':int(r[0]),'open':float(r[1]),'high':float(r[2]),'low':float(r[3]),'close':float(r[4])} for r in p.get('data',[]) if len(r)>=9 and str(r[8])=='1']
    rows.sort(key=lambda z:z['ts'])
    if len(rows)<20:raise RuntimeError('insufficient completed 4H candles')
    latest=rows[-1]; prev3=rows[-4:-1]; prev6=rows[-7:-1]
    confirm=latest['close']>max(x['high'] for x in prev3); newlow=latest['low']<min(x['low'] for x in prev6)
    trs=[max(rows[i]['high']-rows[i]['low'],abs(rows[i]['high']-rows[i-1]['close']),abs(rows[i]['low']-rows[i-1]['close'])) for i in range(1,len(rows))]
    atr=statistics.fmean(trs[-14:]); swing=min(x['low'] for x in prev6); stop=swing-.5*atr; stop_atr=(latest['close']-stop)/atr if atr>0 else None
    ts=datetime.fromtimestamp(latest['ts']/1000,tz=timezone.utc); age=(now-ts).total_seconds()/3600
    return {'price':latest['close'],'timestamp':ts.isoformat(),'age_h':age,'fresh':age<=8,'price_confirm_4h':confirm,'new_local_low_4h':newlow,'atr14_4h':atr,'swing_low_4h':swing,'stop_price':stop,'stop_atr':stop_atr}

def _oi_point(row):
    if isinstance(row,dict):
        ts=row.get('ts'); val=row.get('oiUsd') or row.get('oiCcy') or row.get('oi'); return (int(ts),float(val)) if ts is not None and val not in (None,'') else None
    if isinstance(row,list) and len(row)>=2:return int(row[0]),float(row[1])

def load_oi(now):
    p=fetch_json(OKX_OI_HISTORY,{'instId':'BTC-USDT-SWAP','period':'4H','limit':100})
    if p.get('code')!='0':raise RuntimeError(p.get('msg'))
    pts=sorted(dict(x for x in (_oi_point(r) for r in p.get('data',[])) if x and x[1]>0).items())
    if len(pts)<30:raise RuntimeError('insufficient OI history')
    vals=[v for _,v in pts]; deltas=[vals[i]/vals[i-6]-1 for i in range(6,len(vals))]; cur=deltas[-1]; p10,p90=percentile(deltas,.10),percentile(deltas,.90)
    regime='DELEVERAGING' if cur<=p10 else 'OVERHEATED' if cur>=p90 and cur>0 else 'MODERATE_BUILD' if cur>.03 else 'STABLE'
    ts=datetime.fromtimestamp(pts[-1][0]/1000,tz=timezone.utc); age=(now-ts).total_seconds()/3600
    return {'regime':regime,'timestamp':ts.isoformat(),'age_h':age,'fresh':age<=12,'oi_value':vals[-1],'delta_24h':cur,'delta_p10':p10,'delta_p90':p90,'points':len(vals)}

def main():
    now=datetime.now(timezone.utc); errors={}
    try:fgi=load_fgi(now)
    except Exception as e:fgi=None;errors['fgi']=repr(e)
    try:market=load_candles(now)
    except Exception as e:market=None;errors['market_4h']=repr(e)
    try:oi=load_oi(now)
    except Exception as e:oi=None;errors['oi']=repr(e)
    crowd_ok=bool(fgi and fgi['fresh']); price_ok=bool(market and market['fresh']); risk_ok=bool(market and market.get('stop_atr') is not None); oi_ok=bool(oi and oi['fresh'])
    coverage=25.0*sum([crowd_ok,price_ok,risk_ok,oi_ok]); core_ready=crowd_ok and price_ok and risk_ok
    radar=EntryRadarInput(fgi['value'] if fgi else None,market['price_confirm_4h'] if market else None,market['new_local_low_4h'] if market else None,oi['regime'] if oi_ok else 'N/A',market['stop_atr'] if market else None,core_ready)
    out=to_dict(radar); out.update({'market':market,'crowd':fgi,'open_interest':oi,'quality':{'coverage_pct':coverage,'status':'DATA READY' if core_ready else 'PARTIAL','crowd':'LIVE' if crowd_ok else 'N/A','price_4h':'LIVE' if price_ok else 'N/A','risk':'LIVE' if risk_ok else 'N/A','oi':'LIVE' if oi_ok else 'N/A','errors':errors},'generated_at_utc':now.isoformat()})
    target=Path('artifacts/btc_entry_radar_live_snapshot.json'); target.parent.mkdir(exist_ok=True); target.write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out,indent=2))
if __name__=='__main__':main()
