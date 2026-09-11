import json
from pathlib import Path

import scripts.prepare_ta_ready_alert as mod


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def event(time: str, status: str = "READY") -> dict:
    return {
        "time": time,
        "ticker": "SBERP",
        "tf": "H1",
        "direction": "LONG",
        "status": status,
        "reason": "Все Safety Gate выполнены",
        "price": 300.0,
        "entry": 301.0,
        "stop": 295.0,
        "tp1": 307.0,
        "tp2": 313.0,
        "tp3": 319.0,
        "rr": 2.0,
    }


def configure(monkeypatch, tmp_path):
    history = tmp_path / "signal_history.json"
    state = tmp_path / "telegram_state.json"
    out = tmp_path / "ready_alert.txt"
    monkeypatch.setattr(mod, "HISTORY", history)
    monkeypatch.setattr(mod, "STATE", state)
    monkeypatch.setattr(mod, "OUT", out)
    return history, state, out


def test_first_run_is_baseline_only(monkeypatch, tmp_path):
    history, state, out = configure(monkeypatch, tmp_path)
    write_json(history, {"updated_at": "2026-09-11T10:00:00+03:00", "events": [event("2026-09-11T10:00:00+03:00")]})
    write_json(state, {"release": "R0.8.2 Telegram READY Alerts", "baseline_time": None, "sent_event_keys": []})
    mod.main()
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["baseline_time"] == "2026-09-11T10:00:00+03:00"
    assert len(saved["sent_event_keys"]) == 1
    assert not out.exists()


def test_new_ready_creates_message(monkeypatch, tmp_path):
    history, state, out = configure(monkeypatch, tmp_path)
    old = event("2026-09-11T10:00:00+03:00")
    new = event("2026-09-11T10:10:00+03:00")
    write_json(history, {"updated_at": "2026-09-11T10:10:00+03:00", "events": [old, new]})
    write_json(state, {"release": "R0.8.2 Telegram READY Alerts", "baseline_time": "2026-09-11T10:00:00+03:00", "sent_event_keys": [mod.event_key(old)]})
    mod.main()
    text = out.read_text(encoding="utf-8")
    assert "новый READY" in text
    assert "SBERP · H1 · LONG" in text
    assert "R/R: 2" in text
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert mod.event_key(new) in saved["sent_event_keys"]


def test_same_ready_is_not_resent(monkeypatch, tmp_path):
    history, state, out = configure(monkeypatch, tmp_path)
    ready = event("2026-09-11T10:10:00+03:00")
    write_json(history, {"updated_at": "2026-09-11T10:20:00+03:00", "events": [ready]})
    write_json(state, {"release": "R0.8.2 Telegram READY Alerts", "baseline_time": "2026-09-11T10:10:00+03:00", "sent_event_keys": [mod.event_key(ready)]})
    mod.main()
    assert not out.exists()
