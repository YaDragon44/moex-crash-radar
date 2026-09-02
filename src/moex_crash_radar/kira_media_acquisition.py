"""Media acquisition layer for Kira portfolio sources.

This module keeps acquisition separate from ASR and semantic parsing.
It supports public YouTube sources through an installed yt-dlp binary and
provides a strict contract for authenticated Telegram downloaders.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True)
class AcquiredMedia:
    source_url: str
    local_path: Path
    provider: str


class TelegramMediaProvider(Protocol):
    def download(self, source_url: str, output_dir: Path) -> Path: ...


def _ensure_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not output_dir.is_dir():
        raise NotADirectoryError(output_dir)


def _host(source_url: str) -> str:
    return (urlparse(source_url).hostname or "").lower()


def acquire_youtube(source_url: str, output_dir: Path) -> AcquiredMedia:
    if _host(source_url) not in {"youtu.be", "youtube.com", "www.youtube.com", "m.youtube.com"}:
        raise ValueError("source is not YouTube")
    binary = shutil.which("yt-dlp")
    if not binary:
        raise RuntimeError("yt-dlp binary is not installed")
    _ensure_output_dir(output_dir)
    template = str(output_dir / "%(id)s.%(ext)s")
    cmd = [
        binary,
        "--no-playlist",
        "--extract-audio",
        "--audio-format", "m4a",
        "--print", "after_move:filepath",
        "-o", template,
        source_url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {proc.stderr.strip()[:500]}")
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("yt-dlp returned no output path")
    path = Path(lines[-1])
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    return AcquiredMedia(source_url=source_url, local_path=path, provider="yt-dlp")


def acquire_telegram(source_url: str, output_dir: Path, provider: TelegramMediaProvider) -> AcquiredMedia:
    if _host(source_url) != "t.me":
        raise ValueError("source is not Telegram")
    _ensure_output_dir(output_dir)
    path = provider.download(source_url, output_dir)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    return AcquiredMedia(source_url=source_url, local_path=path, provider=provider.__class__.__name__)
