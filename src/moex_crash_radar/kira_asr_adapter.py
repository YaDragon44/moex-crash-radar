"""ASR adapter contract for Kira portfolio audio.

The adapter is intentionally provider-neutral. Production can supply Whisper or
another ASR implementation without coupling media acquisition to portfolio
semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .kira_audio_parser import TranscriptSegment


class AsrProvider(Protocol):
    def transcribe(self, media_path: Path, *, language: str = "ru") -> list[TranscriptSegment]: ...


@dataclass(frozen=True)
class MediaInput:
    source_url: str
    local_path: Path


def transcribe_media(media: MediaInput, provider: AsrProvider) -> list[TranscriptSegment]:
    if not media.source_url.startswith(("https://t.me/", "https://youtu.be/", "https://www.youtube.com/")):
        raise ValueError("unsupported source URL")
    if not media.local_path.exists() or not media.local_path.is_file():
        raise FileNotFoundError(media.local_path)
    segments = provider.transcribe(media.local_path, language="ru")
    return [s for s in segments if s.text.strip() and s.end_s >= s.start_s >= 0]
