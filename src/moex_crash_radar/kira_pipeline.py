"""End-to-end orchestration for Kira public portfolio media.

source URL -> acquired media -> ASR transcript -> semantic portfolio changes.
The orchestrator preserves source provenance and never enriches missing trade
fields beyond what the transcript parser can prove.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from .kira_asr_adapter import AsrProvider, MediaInput, transcribe_media
from .kira_audio_parser import PortfolioChange, parse_transcript, serialize
from .kira_media_acquisition import (
    TelegramMediaProvider,
    acquire_telegram,
    acquire_youtube,
)


@dataclass(frozen=True)
class PipelineResult:
    source_url: str
    media_provider: str
    media_path: str
    transcript_segments: int
    changes: tuple[PortfolioChange, ...]

    def to_dict(self) -> dict:
        return {
            "source_url": self.source_url,
            "media_provider": self.media_provider,
            "media_path": self.media_path,
            "transcript_segments": self.transcript_segments,
            "changes": serialize(self.changes),
        }


def _host(source_url: str) -> str:
    return (urlparse(source_url).hostname or "").lower()


def run_pipeline(
    source_url: str,
    *,
    output_dir: Path,
    asr_provider: AsrProvider,
    telegram_provider: TelegramMediaProvider | None = None,
) -> PipelineResult:
    host = _host(source_url)
    if host == "t.me":
        if telegram_provider is None:
            raise RuntimeError("Telegram source requires an authenticated media provider")
        media = acquire_telegram(source_url, output_dir, telegram_provider)
    elif host in {"youtu.be", "youtube.com", "www.youtube.com", "m.youtube.com"}:
        media = acquire_youtube(source_url, output_dir)
    else:
        raise ValueError("unsupported source URL")

    segments = transcribe_media(
        MediaInput(source_url=source_url, local_path=media.local_path),
        asr_provider,
    )
    changes = tuple(parse_transcript(segments, source_url))
    return PipelineResult(
        source_url=source_url,
        media_provider=media.provider,
        media_path=str(media.local_path),
        transcript_segments=len(segments),
        changes=changes,
    )
