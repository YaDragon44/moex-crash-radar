from datetime import datetime,timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import strategy3_value_rsi as s3
BASE=datetime(2026,1,1,tzinfo=ZoneInfo("Europe/Moscow"))
def candles(v):return [SimpleNamespace(close=x,end=BASE+timedelta(minutes=10*i)) for i,x in enumerate(v)]
def consensus(target=150):return {"status":"OK","consensus_target":target,"target_low":120,"target_high":200}
def test_rsi_bounds(): assert 0<=s3.rsi(list(range(1,220)))<=100
def test_watch_when_oversold_below_trend():
    v=[150.0]*180+[150-i*2 for i in range(1,22)]
    r=s3.evaluate(candles(v),consensus(200));assert r["rsi14"]<30;assert r["decision"] in {"WATCH","BUY"}
def test_fair_value_required():
    try:s3.evaluate(candles([100.0]*201),{"status":"DATA_UNAVAILABLE"})
    except ValueError as e:assert "FAIR_VALUE" in str(e)
    else:assert False
