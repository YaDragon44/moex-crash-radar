from pathlib import Path

import pytest

from moex_crash_radar.kira_media_acquisition import acquire_telegram, acquire_youtube


class FakeTelegramProvider:
    def __init__(self, create_file: bool = True):
        self.create_file = create_file

    def download(self, source_url: str, output_dir: Path) -> Path:
        path = output_dir / "5728.ogg"
        if self.create_file:
            path.write_bytes(b"audio")
        return path


def test_telegram_source_rejects_wrong_host(tmp_path):
    with pytest.raises(ValueError):
        acquire_telegram("https://example.com/5728", tmp_path, FakeTelegramProvider())


def test_telegram_provider_must_create_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        acquire_telegram("https://t.me/kira_pronira/5728", tmp_path, FakeTelegramProvider(False))


def test_telegram_success(tmp_path):
    media = acquire_telegram("https://t.me/kira_pronira/5728", tmp_path, FakeTelegramProvider())
    assert media.local_path.exists()
    assert media.provider == "FakeTelegramProvider"


def test_youtube_rejects_wrong_host(tmp_path):
    with pytest.raises(ValueError):
        acquire_youtube("https://example.com/video", tmp_path)
