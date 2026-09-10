from __future__ import annotations

import json, statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LEDGER=Path('artifacts/r1_4_5_trade_ledger.json')
OUT=Path('artifacts/r1_4_6_entry_core_diagnostic.json')
COST=5

def mean(xs): return round(statistics.fmean(xs),2) if xs else None

def cell(es):
 xs=[float(e['gross_bps'])-COST for e in es]
 return {'n':len(xs),'mean_net_bps':mean(xs),'median_net_bps':round(statistics.median(xs),2) if xs else None,'positive_pct':round(100*sum(x>0 for x in xs)/len(xs),2) if xs else None,'cum_net_bps':round(sum(xs),2) if xs else 0,'mean_mae_bps':mean([float(e['mae_bps']) for e in es]),'mean_mfe_bps':mean([float(e['mfe_bps']) for e in es]),'stop_pct':round(100*sum(e['exit_reason']=='STOP' for e in es)/len(es),2) if es else None}

def group(es,key):
 d=defaultdict(list)
 for e in es:d[str(key(e))].append(e)
 return {k:cell(v) for k,v in sorted(d.items())}

def main():
 es=json.loads(LEDGER.read_text(encoding='utf-8'))
 oos=[e for e in es if e['split']=='OOS']
 report={'release':'R1.4.6','source':'R1.4.5 frozen trade ledger','cost_bps':COST,'oos':cell(oos)}
 report['by_side']=group(oos,lambda e:e['side'])
 report['by_family']=group(oos,lambda e:e['family'])
 report['by_exit']=group(oos,lambda e:e['exit_reason'])
 report['by_month']=group(oos,lambda e:e['signal_time'][:7])
 report['by_quarter']=group(oos,lambda e:f"{e['signal_time'][:4]}-Q{(int(e['signal_time'][5:7])-1)//3+1}")
 report['by_hour']=group(oos,lambda e:datetime.fromisoformat(e['signal_time']).hour)
 fam=sorted(report['by_family'].items(),key=lambda kv:kv[1]['cum_net_bps'])
 report['concentration']={'worst_families':fam[:3],'best_families':fam[-3:]}
 report['diagnosis']={
  'broad_failure': sum(v['mean_net_bps']>0 for v in report['by_family'].values()) < max(1,len(report['by_family'])*0.5),
  'long_mean':report['by_side'].get('LONG',{}).get('mean_net_bps'),
  'short_mean':report['by_side'].get('SHORT',{}).get('mean_net_bps'),
  'ng_mean':report['by_family'].get('NG',{}).get('mean_net_bps'),
  'interpretation':'Entry core failure is broad if fewer than half of OOS families have positive mean after 5 bps; do not rescue with extra indicators before redesign.'}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report['diagnosis'],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
