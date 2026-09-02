import os

import pytest

from moex_crash_radar.kira_runtime_providers import (
    TelegramRuntimeConfig,
    TelethonMediaProvider,
)


def test_telegram_config_requires_credentials(monkeypatch):
    monkeypatch.delenv("KIRA_TG_API_ID", raising=False)
    monkeypatch.delenv("KIRA_TG_API_HASH", raising=False)
    with pytest.raises(RuntimeError):
        TelegramRuntimeConfig.from_env()


def test_telegram_config_rejects_bad_api_id(monkeypatch):
    monkeypatch.setenv("KIRA_TG_API_ID", "abc")
    monkeypatch.setenv("KIRA_TG_API_HASH", "hash")
    with pytest.raises(RuntimeError):
        TelegramRuntimeConfig.from_env()


def test_public_post_parser():
    assert TelethonMediaProvider._parse_public_post("https://t.me/kira_pronira/5728") == ("kira_pronira", 5728)


def test_public_post_parser_rejects_preview_url():
    with pytest.raises(ValueError):
        TelethonMediaProvider._parse_public_post("https://t.me/s/kira_pronira?before=5729")
