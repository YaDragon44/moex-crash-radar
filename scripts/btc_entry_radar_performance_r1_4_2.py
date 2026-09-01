from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

JOURNAL = Path('evidence/btc_entry_radar_journal.csv')
OUT = Path('artifacts/btc_entry_radar_performance.json')
TRACKED = {'WATCH','ARMED','LONG_READY'}
HORIZONS = {'24h': 6, '72h': 18, '7d': 42}  # 4H bars
OKX = 'https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=4H&limit=300'


def fetch_candles():
    req=Request(OKX, headers={'User-Agent':'btc-entry-radar/1.4.2'})
    with urlopen(req, timeout=20) as r:
        p=json.loads(r.read().decode())
    rows=[]
    for x in p['data']:
        rows.append({'ts':datetime.fromtimestamp(int(x[0])/1000, tz=timezone.utc),
                     'o':float(x[1]),'h':float(x[2]),'l':float(x[3]),'c':float(x[4])})
    return sorted(rows, key=lambda x:x['ts'])


def load_signals():
    if not JOURNAL.exists(): return []
    with JOURNAL.open(encoding='utf-8', newline='') as f:
        return [r for r in csv.DictReader(f) if r.get('state') in TRACKED and r.get('price')]


def score(signal, candles):
    t=datetime.fromisoformat(signal['generated_at_utc'].replace('Z','+00:00'))
    future=[x for x in candles if x['ts'] >= t]
    if not future: return None
    entry=float(signal['price'])
    result={'signal_time':signal['generated_at_utc'],'state':signal['state'],'entry_price':entry,'horizons':{}}
    for name,n in HORIZONS.items():
        sample=future[:n]
        if len(sample)<n: continue
        close=sample[-1]['c']
        mfe=max(x['h'] for x in sample)/entry-1
        mae=min(x['l'] for x in sample)/entry-1
        result['horizons'][name]={'forward_return':close/entry-1,'mfe':mfe,'mae':mae,'bars':n}
    return result


def main():
    signals=load_signals()
    candles=fetch_candles()
    scored=[x for s in signals if (x:=score(s,candles)) is not None]
    summary={}
    for state in sorted(TRACKED):
        ss=[x for x in scored if x['state']==state]
        summary[state]={'signals':len(ss)}
        for h in HORIZONS:
            vals=[x['horizons'][h] for x in ss if h in x['horizons']]
            if vals:
                summary[state][h]={
                    'n':len(vals),
                    'avg_forward_return':sum(v['forward_return'] for v in vals)/len(vals),
                    'avg_mfe':sum(v['mfe'] for v in vals)/len(vals),
                    'avg_mae':sum(v['mae'] for v in vals)/len(vals),
                    'positive_rate':sum(v['forward_return']>0 for v in vals)/len(vals)
                }
    payload={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
             'tracked_states':sorted(TRACKED),'signal_count':len(signals),'scored_count':len(scored),
             'summary':summary,'signals':scored,
             'interpretation':'Descriptive shadow statistics only; not calibrated probabilities or proof of edge.'}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))

if __name__=='__main__': main()
