from __future__ import annotations
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RELEASE='R1.5.1'
FAMILIES={'MX':'MX','SI':'Si','SR':'SR','GZ':'GZ'}
BASE='https://iss.moex.com/iss/engines/futures/markets/forts/securities.json'


def get_json(url:str)->dict:
    req=urllib.request.Request(url,headers={'User-Agent':'moex-crash-radar-r1.5.1'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def table(payload:dict,name:str)->list[dict]:
    x=payload.get(name) or {}; cols=x.get('columns') or []
    return [dict(zip(cols,row)) for row in (x.get('data') or [])]


def audit_family(label:str,prefix:str)->dict:
    # Public ISS instrument/market snapshot is audited only for explicit OI fields.
    q=urllib.parse.urlencode({'iss.meta':'off','iss.only':'securities,marketdata','securities.columns':'SECID,SHORTNAME,LASTTRADEDATE','marketdata.columns':'SECID,SYSTIME,OPENPOSITION,OPENPOSITIONVALUE'})
    try:
        p=get_json(BASE+'?'+q); sec=table(p,'securities'); md=table(p,'marketdata')
    except Exception as exc:
        return {'family':label,'source':'MOEX_ISS_FORTS','quality':'N/A','error':repr(exc),'historical_point_in_time_ready':False}
    candidates=[r for r in sec if str(r.get('SECID') or '').upper().startswith(prefix.upper())]
    ids={r.get('SECID') for r in candidates}; rows=[r for r in md if r.get('SECID') in ids]
    oi_rows=[r for r in rows if r.get('OPENPOSITION') is not None or r.get('OPENPOSITIONVALUE') is not None]
    return {
      'family':label,'source':'MOEX_ISS_FORTS','access':'PUBLIC','quality':'DELAYED' if oi_rows else 'N/A',
      'candidate_contracts':len(candidates),'snapshot_rows_with_oi':len(oi_rows),
      'fields_observed':['OPENPOSITION','OPENPOSITIONVALUE'] if oi_rows else [],
      'event_time_semantics':'current market snapshot; not sufficient for historical PIT backtest',
      'available_time_semantics':'SYSTIME when present',
      'first_timestamp':None,'last_timestamp':max([r.get('SYSTIME') for r in oi_rows if r.get('SYSTIME')],default=None),
      'frequency':'SNAPSHOT','contract_coverage':[r.get('SECID') for r in oi_rows[:20]],'gaps':'historical coverage not established',
      'historical_point_in_time_ready':False
    }


def main():
    audits=[audit_family(k,v) for k,v in FAMILIES.items()]
    ready=[a for a in audits if a.get('historical_point_in_time_ready')]
    result={
      'release':RELEASE,'generated_at':datetime.now(timezone.utc).isoformat(),'production':'NO-GO','families':audits,
      'futoi_positioning':'BLOCKED_AUTH','data_ready_families':len(ready),
      'gate':{'status':'DATA_READY' if len(ready)>=2 else 'DATA_LIMITED','m1_backtest_allowed':len(ready)>=2,'reason':'Historical point-in-time OI coverage must be proven for >=2 families and >=2 chronological subperiods.'}
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/r1_5_1_oi_availability.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
