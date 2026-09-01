from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.btc_entry_radar_r1_4_0 import EntryRadarInput,evaluate

def test_no_trade_on_bad_quality(): assert evaluate(EntryRadarInput(None,None,None,'N/A',None,False)).state=='NO_TRADE'
def test_greed_veto_partial(): assert evaluate(EntryRadarInput(69,None,None,'N/A',None,False)).action=='DO NOT CHASE'
def test_watch(): assert evaluate(EntryRadarInput(20,False,True,'DELEVERAGING',1.0,True)).state=='WATCH'
def test_armed(): assert evaluate(EntryRadarInput(30,False,False,'STABLE',1.2,True)).state=='ARMED'
def test_long_ready_best():
    r=evaluate(EntryRadarInput(20,True,False,'DELEVERAGING',1.0,True)); assert r.state=='LONG_READY' and r.standard_size==1.0
def test_long_ready_reduced(): assert evaluate(EntryRadarInput(30,True,False,'MODERATE_BUILD',1.0,True)).standard_size==0.5
def test_no_trade_overheated(): assert evaluate(EntryRadarInput(20,True,False,'OVERHEATED',1.0,True)).state=='NO_TRADE'
def test_no_trade_wide_stop(): assert evaluate(EntryRadarInput(20,True,False,'DELEVERAGING',2.1,True)).state=='NO_TRADE'
def test_manage(): assert evaluate(EntryRadarInput(75,True,False,'OVERHEATED',1.0,True,True)).state=='MANAGE'
