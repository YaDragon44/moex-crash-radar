from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import strategy4_h1 as s
import monitor
Z=ZoneInfo("Europe/Moscow")
def candles(n=30):
    t=datetime(2026,9,1,10,tzinfo=Z);out=[]
    for i in range(n):
        p=100+i*.05
        out.append(monitor.Candle(t+i*timedelta(hours=1),t+(i+1)*timedelta(hours=1),p,p,p+.2,p-.2,1000))
    return out
def test_wait(): assert s.evaluate(candles())["decision"]=="WAIT"
def test_contract():
    x=s.evaluate(candles());assert x["strategy"]=="S4_ADAPTIVE_H1";assert x["timeframe"]=="H1";assert x["mode"]=="SHADOW"
