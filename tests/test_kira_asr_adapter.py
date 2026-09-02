from pathlib import Path

import pytest

from moex_crash_radar.kira_asr_adapter import MediaInput, transcribe_media
from moex_crash_radar.kira_audio_parser import TranscriptSegment


class FakeAsr:
    def transcribe(self, media_path: Path, *, language: str = "ru"):
        assert language == "ru"
        return [
            TranscriptSegment(0, 2, "  "),
            TranscriptSegment(2, 4, "Докупаю Озон Фармацевтику"),
            TranscriptSegment(5, 4, "bad timestamp"),
        ]


def test_adapter_filters_empty_and_invalid_segments(tmp_path):
    p = tmp_path / "sample.mp3"
    p.write_bytes(b"fake")
    result = transcribe_media(MediaInput("https://t.me/kira_pronira/5728", p), FakeAsr())
    assert result == [TranscriptSegment(2, 4, "Докупаю Озон Фармацевтику")]


def test_missing_media_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        transcribe_media(MediaInput("https://t.me/kira_pronira/5728", tmp_path / "missing.mp3"), FakeAsr())


def test_untrusted_source_is_rejected(tmp_path):
    p = tmp_path / "sample.mp3"
    p.write_bytes(b"fake")
    with pytest.raises(ValueError):
        transcribe_media(MediaInput("https://example.com/audio.mp3", p), FakeAsr())
