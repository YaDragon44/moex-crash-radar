from pathlib import Path

from moex_crash_radar import kira_live_runner as runner


SOURCE = "https://t.me/kira_pronira/5728"


def test_missing_runtime_and_credentials_are_blocked(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("KIRA_TG_API_ID", raising=False)
    monkeypatch.delenv("KIRA_TG_API_HASH", raising=False)
    monkeypatch.setattr(runner.importlib.util, "find_spec", lambda _name: None)

    report = runner.diagnose_live(SOURCE, output_dir=tmp_path)

    assert report.status == "BLOCKED_ENV"
    assert report.result is None
    assert {g.name: g.status for g in report.gates}["live_pipeline"] == "NOT_RUN"


def test_ready_environment_can_be_checked_without_execution(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KIRA_TG_API_ID", "123")
    monkeypatch.setenv("KIRA_TG_API_HASH", "abc")
    monkeypatch.setattr(runner.importlib.util, "find_spec", lambda _name: object())

    report = runner.diagnose_live(SOURCE, output_dir=tmp_path, execute=False)

    assert report.status == "NOT_RUN"
    assert report.result is None
    assert all(g.status == "PASS" for g in report.gates[:-1])


def test_live_pipeline_pass_is_reported(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KIRA_TG_API_ID", "123")
    monkeypatch.setenv("KIRA_TG_API_HASH", "abc")
    monkeypatch.setattr(runner.importlib.util, "find_spec", lambda _name: object())

    class Result:
        transcript_segments = 3
        def to_dict(self):
            return {"source_url": SOURCE, "transcript_segments": 3, "changes": []}

    monkeypatch.setattr(runner, "run_pipeline", lambda *args, **kwargs: Result())

    report = runner.diagnose_live(SOURCE, output_dir=tmp_path)

    assert report.status == "PASS"
    assert report.result["transcript_segments"] == 3


def test_runtime_error_is_fail_not_pass(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KIRA_TG_API_ID", "123")
    monkeypatch.setenv("KIRA_TG_API_HASH", "abc")
    monkeypatch.setattr(runner.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(runner, "run_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("media unavailable")))

    report = runner.diagnose_live(SOURCE, output_dir=tmp_path)

    assert report.status == "FAIL"
    assert report.result is None
