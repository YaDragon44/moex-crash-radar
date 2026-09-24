from pathlib import Path

from decision_audit import append_if_changed


def test_decision_audit_deduplicates_identical_state(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    base = {"timestamp": "2026-09-24T10:00:00+03:00", "candle": "c1", "status": "WAIT", "reason": "NO_TRIGGER"}
    assert append_if_changed(base, path) is True
    later = dict(base, timestamp="2026-09-24T10:01:00+03:00")
    assert append_if_changed(later, path) is False
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_decision_audit_records_changed_candle(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    assert append_if_changed({"timestamp": "t1", "candle": "c1", "status": "WAIT"}, path)
    assert append_if_changed({"timestamp": "t2", "candle": "c2", "status": "WAIT"}, path)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
