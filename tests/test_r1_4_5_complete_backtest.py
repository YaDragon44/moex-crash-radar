from scripts.run_r1_4_5_complete_backtest import third_thursday,sub_weekdays,split_of,events,metrics
from datetime import date, datetime, timedelta

def test_calendar_helpers():
 assert third_thursday(2026,9)==date(2026,9,17)
 assert sub_weekdays(date(2026,9,17),5)==date(2026,9,10)

def test_split_boundaries():
 assert split_of('2024-12-31 18:00:00')=='IS'
 assert split_of('2025-01-01 10:00:00')=='VALIDATION'
 assert split_of('2026-01-01 10:00:00')=='OOS'

def _bars(n=70,contract='MXU6'):
 out=[]
 p=100.0
 t=datetime(2026,1,1,10,0,0)
 for i in range(n):
  p+=1
  out.append({'begin':(t+timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'),'open':p-.2,'high':p+.5,'low':p-.5,'close':p,'secid':contract,'roll_date':'2026-09-10'})
 return out

def test_next_bar_open_and_no_cross_contract_leakage():
 rows=_bars()
 es=events(rows)
 assert es
 e=es[0]
 sig_i=next(i for i,r in enumerate(rows) if r['begin']==e['signal_time'])
 assert e['entry_time']==rows[sig_i+1]['begin']
 assert e['entry']==rows[sig_i+1]['open']
 rows[sig_i+1]['secid']='MXZ6'
 es2=events(rows)
 assert all(not (x['signal_time']==e['signal_time']) for x in es2)

def test_cost_once_and_drawdown():
 es=[{'gross_bps':10,'exit_reason':'TIME','holding_bars':8},{'gross_bps':-20,'exit_reason':'STOP','holding_bars':2},{'gross_bps':15,'exit_reason':'TIME','holding_bars':8}]
 m=metrics(es,5)
 assert m['cum_bps']==-10
 assert m['max_drawdown_bps']==25
