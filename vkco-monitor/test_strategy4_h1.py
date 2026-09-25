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

def test_signal_contract_has_lifecycle_fields():
    c=candles()
    for i in range(7,27):
        c[i]=monitor.Candle(c[i].begin,c[i].end,100,100,100.2,99.8,1000)
    c[-3]=monitor.Candle(c[-3].begin,c[-3].end,100,100,100.2,99.8,1000)
    c[-2]=monitor.Candle(c[-2].begin,c[-2].end,100,101,101.2,100,1300)
    c[-1]=monitor.Candle(c[-1].begin,c[-1].end,101,101.1,101.3,100.8,1200)
    x=s.evaluate(c)
    assert x["decision"]=="READY"
    assert x["signal"]["signal_id"].startswith("S4:H1:")
    assert x["signal"]["time"]==x["candle"]
    assert x["signal"]["price"]==x["signal"]["entry"]

def test_public_snapshot_exposes_trade_stats(monkeypatch,tmp_path):
    monkeypatch.setattr(s,"STATE_FILE",tmp_path/"state.json")
    monkeypatch.setattr(s,"JOURNAL_FILE",tmp_path/"journal.jsonl")
    x=s.public_snapshot(candles())
    assert x["closed_trades"]==0
    assert x["expectancy_r"] is None
