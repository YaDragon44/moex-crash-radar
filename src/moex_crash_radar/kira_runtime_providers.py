"""Concrete runtime providers for Kira media + ASR.

Telegram: Telethon user session (MTProto), required for arbitrary public channel
history/media. ASR: faster-whisper local model. Both are optional runtime deps;
core package stays lightweight and tests can run without them.
"""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import os
from pathlib import Path
import re

from .kira_audio_parser import TranscriptSegment


@dataclass(frozen=True)
class TelegramRuntimeConfig:
    api_id: int
    api_hash: str
    session: str

    @classmethod
    def from_env(cls) -> "TelegramRuntimeConfig":
        api_id = os.getenv("KIRA_TG_API_ID", "").strip()
        api_hash = os.getenv("KIRA_TG_API_HASH", "").strip()
        session = os.getenv("KIRA_TG_SESSION", "kira_portfolio").strip() or "kira_portfolio"
        if not api_id or not api_hash:
            raise RuntimeError("KIRA_TG_API_ID and KIRA_TG_API_HASH are required")
        try:
            parsed_id = int(api_id)
        except ValueError as exc:
            raise RuntimeError("KIRA_TG_API_ID must be an integer") from exc
        return cls(api_id=parsed_id, api_hash=api_hash, session=session)


class TelethonMediaProvider:
    def __init__(self, config: TelegramRuntimeConfig):
        self.config = config

    @staticmethod
    def _parse_public_post(source_url: str) -> tuple[str, int]:
        match = re.fullmatch(r"https://t\.me/([A-Za-z0-9_]+)/([0-9]+)/?", source_url)
        if not match:
            raise ValueError("expected public Telegram post URL https://t.me/<channel>/<post_id>")
        return match.group(1), int(match.group(2))

    def download(self, source_url: str, output_dir: Path) -> Path:
        try:
            from telethon import TelegramClient
        except ImportError as exc:
            raise RuntimeError("Telethon is not installed; install runtime extra 'kira-runtime'") from exc

        channel, post_id = self._parse_public_post(source_url)
        output_dir.mkdir(parents=True, exist_ok=True)

        async def _download() -> Path:
            async with TelegramClient(self.config.session, self.config.api_id, self.config.api_hash) as client:
                message = await client.get_messages(channel, ids=post_id)
                if not message:
                    raise RuntimeError(f"Telegram post not found: {channel}/{post_id}")
                if not message.media:
                    raise RuntimeError(f"Telegram post has no downloadable media: {channel}/{post_id}")
                target = await client.download_media(message, file=str(output_dir))
                if not target:
                    raise RuntimeError("Telethon returned no media path")
                path = Path(target)
                if not path.exists() or not path.is_file():
                    raise FileNotFoundError(path)
                return path

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_download())
        raise RuntimeError("TelethonMediaProvider.download must run outside an active asyncio event loop")


@dataclass(frozen=True)
class FasterWhisperConfig:
    model_size: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"


class FasterWhisperProvider:
    def __init__(self, config: FasterWhisperConfig | None = None):
        self.config = config or FasterWhisperConfig()
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed; install runtime extra 'kira-runtime'") from exc
        self._model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )
        return self._model

    def transcribe(self, media_path: Path, *, language: str = "ru") -> list[TranscriptSegment]:
        model = self._get_model()
        segments, _info = model.transcribe(
            str(media_path),
            language=language,
            vad_filter=True,
        )
        out: list[TranscriptSegment] = []
        for seg in segments:
            text = (getattr(seg, "text", "") or "").strip()
            start = float(getattr(seg, "start", 0.0))
            end = float(getattr(seg, "end", start))
            if text and end >= start >= 0:
                out.append(TranscriptSegment(start_s=start, end_s=end, text=text))
        return out
