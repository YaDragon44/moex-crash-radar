"""Live diagnostic runner for Kira portfolio audio pipeline.

Reports PASS / BLOCKED_ENV / FAIL per stage without fabricating portfolio data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import json
from pathlib import Path
from typing import Literal

from .kira_pipeline import run_pipeline
from .kira_runtime_providers import (
    FasterWhisperProvider,
    TelegramRuntimeConfig,
    TelethonMediaProvider,
)

Status = Literal["PASS", "BLOCKED_ENV", "FAIL", "NOT_RUN"]


@dataclass(frozen=True)
class Gate:
    name: str
    status: Status
    detail: str


@dataclass(frozen=True)
class LiveDiagnostic:
    source_url: str
    gates: tuple[Gate, ...]
    result: dict | None

    @property
    def status(self) -> Status:
        statuses = {g.status for g in self.gates}
        if "FAIL" in statuses:
            return "FAIL"
        if "BLOCKED_ENV" in statuses:
            return "BLOCKED_ENV"
        if statuses <= {"PASS"}:
            return "PASS"
        return "NOT_RUN"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "source_url": self.source_url,
            "gates": [asdict(g) for g in self.gates],
            "result": self.result,
        }


def _dependency_gate(module: str, label: str) -> Gate:
    if importlib.util.find_spec(module) is None:
        return Gate(label, "BLOCKED_ENV", f"Python module '{module}' is not installed")
    return Gate(label, "PASS", "available")


def diagnose_live(
    source_url: str,
    *,
    output_dir: Path,
    execute: bool = True,
) -> LiveDiagnostic:
    gates: list[Gate] = []

    telethon_gate = _dependency_gate("telethon", "telegram_runtime")
    whisper_gate = _dependency_gate("faster_whisper", "asr_runtime")
    gates.extend((telethon_gate, whisper_gate))

    try:
        tg_config = TelegramRuntimeConfig.from_env()
        gates.append(Gate("telegram_credentials", "PASS", "configured"))
    except RuntimeError as exc:
        gates.append(Gate("telegram_credentials", "BLOCKED_ENV", str(exc)))
        tg_config = None

    if any(g.status == "BLOCKED_ENV" for g in gates):
        gates.append(Gate("live_pipeline", "NOT_RUN", "environment prerequisites are incomplete"))
        return LiveDiagnostic(source_url, tuple(gates), None)

    if not execute:
        gates.append(Gate("live_pipeline", "NOT_RUN", "execution disabled"))
        return LiveDiagnostic(source_url, tuple(gates), None)

    try:
        result = run_pipeline(
            source_url,
            output_dir=output_dir,
            asr_provider=FasterWhisperProvider(),
            telegram_provider=TelethonMediaProvider(tg_config),
        )
    except (ValueError, FileNotFoundError) as exc:
        gates.append(Gate("live_pipeline", "FAIL", f"{type(exc).__name__}: {exc}"))
        return LiveDiagnostic(source_url, tuple(gates), None)
    except RuntimeError as exc:
        # Runtime failures after prerequisites passed are source/runtime failures,
        # not evidence for a trade and not silently downgraded to PASS.
        gates.append(Gate("live_pipeline", "FAIL", str(exc)))
        return LiveDiagnostic(source_url, tuple(gates), None)

    gates.append(Gate("live_pipeline", "PASS", f"{result.transcript_segments} transcript segments"))
    return LiveDiagnostic(source_url, tuple(gates), result.to_dict())


def write_diagnostic(report: LiveDiagnostic, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
