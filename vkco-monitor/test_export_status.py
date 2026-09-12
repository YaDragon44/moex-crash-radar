from __future__ import annotations

import json
from datetime import timedelta

import export_status
import monitor


def _candles(now, count=30, stale=False):
    out=[]
    for i in range(count):
        end=now-timedelta(minutes=(count-i)*10)
        if stale:
            end=end-timedelta(days=1)
        px=118.0+i*0.03
        out.append(monitor.Candle(
            begin=end-timedelta(minutes=10), end=end,
            open=px-0.05, close=px, high=px+0.15, low=px-0.15, volume=1000+i,
        ))
    return out


def test_active_position_is_exposed_without_secrets(tmp_path, monkeypatch):
    state_path=tmp_path/'state.json'
    journal_path=tmp_path/'journal.jsonl'
    state={
        'last_signal_id':'x',
        'position':{
            'ticker':'VKCO','direction':'LONG','status':'OPEN','signal_id':'x',
            'opened_at':'2026-09-12T10:00:00+03:00','entry':120.0,'stop':116.0,
            'tp1':126.0,'tp2':130.0,'tp3':136.0,'shares':100,'lots':100,
            'initial_risk_rub':400.0,'setup':'Adaptive Breakout + Hold','score':14,
            'last_event':'OPEN','last_price':121.0,
            'private_field':'must_not_leak',
        },
    }
    state_path.write_text(json.dumps(state),encoding='utf-8')
    monkeypatch.setattr(export_status.monitor,'STATE_FILE',state_path)
    monkeypatch.setattr(export_status,'JOURNAL_JSONL',journal_path)
    now=monitor.datetime.now(monitor.MOSCOW)
    monkeypatch.setattr(export_status.monitor,'fetch_candles',lambda *a,**k:_candles(now))

    payload=export_status.build_status()

    assert payload['trade']['status']=='OPEN'
    assert payload['position']['entry']==120.0
    assert 'private_field' not in payload['position']
    assert 'TELEGRAM_BOT_TOKEN' not in json.dumps(payload)


def test_stale_market_is_wait(tmp_path, monkeypatch):
    state_path=tmp_path/'state.json'
    state_path.write_text('{}',encoding='utf-8')
    monkeypatch.setattr(export_status.monitor,'STATE_FILE',state_path)
    monkeypatch.setattr(export_status,'JOURNAL_JSONL',tmp_path/'journal.jsonl')
    now=monitor.datetime.now(monitor.MOSCOW)
    monkeypatch.setattr(export_status.monitor,'fetch_candles',lambda *a,**k:_candles(now,stale=True))

    payload=export_status.build_status()

    assert payload['trade']=={'status':'WAIT','reason':'STALE_OR_MARKET_CLOSED'}
    assert payload['market']['fresh'] is False


def test_export_error_degrades_but_writes_json(tmp_path, monkeypatch):
    out=tmp_path/'status.json'
    monkeypatch.setattr(export_status,'build_status',lambda: (_ for _ in ()).throw(RuntimeError('boom')))

    payload=export_status.export_status(out)

    assert payload['health']=='DEGRADED'
    saved=json.loads(out.read_text(encoding='utf-8'))
    assert saved['trade']['reason']=='STATUS_EXPORT_ERROR'
