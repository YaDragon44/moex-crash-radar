from pathlib import Path

import pytest

from moex_crash_radar.kira_audio_parser import TranscriptSegment
from moex_crash_radar.kira_pipeline import run_pipeline


class FakeTelegramProvider:
    def download(self, source_url: str, output_dir: Path) -> Path:
        path = output_dir / "audio.m4a"
        path.write_bytes(b"fake")
        return path


class FakeAsr:
    def transcribe(self, media_path: Path, *, language: str = "ru"):
        assert media_path.exists()
        assert language == "ru"
        return [
            TranscriptSegment(0, 4, "Докупаю Озон Фармацевтику"),
            TranscriptSegment(5, 8, "Мне нравится отчет Интер РАО"),
            TranscriptSegment(9, 12, "Покупаю одну компанию"),
        ]


def test_telegram_e2e_preserves_unknowns(tmp_path):
    result = run_pipeline(
        "https://t.me/kira_pronira/5728",
        output_dir=tmp_path,
        asr_provider=FakeAsr(),
        telegram_provider=FakeTelegramProvider(),
    )
    assert result.transcript_segments == 3
    assert len(result.changes) == 2
    assert result.changes[0].action == "ADD"
    assert result.changes[0].asset == "OZPH"
    assert result.changes[0].amount is None
    assert result.changes[1].action == "BUY"
    assert result.changes[1].asset is None
    assert result.changes[1].source_url.endswith("/5728")


def test_telegram_requires_authenticated_provider(tmp_path):
    with pytest.raises(RuntimeError):
        run_pipeline(
            "https://t.me/kira_pronira/5728",
            output_dir=tmp_path,
            asr_provider=FakeAsr(),
        )


def test_unsupported_source_rejected(tmp_path):
    with pytest.raises(ValueError):
        run_pipeline(
            "https://example.com/audio",
            output_dir=tmp_path,
            asr_provider=FakeAsr(),
        )
