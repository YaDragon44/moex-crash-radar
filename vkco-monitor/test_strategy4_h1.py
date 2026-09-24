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

def test_h1_market_filter():
    c=candles()
    x=s.h1_market_filter(c)
    assert "ok" in x and "return_1h_pct" in x

def test_decision_wait_does_not_fetch_gates(monkeypatch):
    monkeypatch.setattr(s,"fetch_h1",lambda *a,**k: (_ for _ in ()).throw(AssertionError("gate should not run")))
    x=s.decision_snapshot(candles())
    assert x["decision"]=="WAIT"
    assert x["imoex"] is None
