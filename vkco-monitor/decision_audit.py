from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

AUDIT_JSONL = Path(os.getenv("DECISION_AUDIT_JSONL", "vkco-monitor/state/decision_audit.jsonl"))


def _fingerprint(snapshot: dict[str, Any]) -> str:
    """Deduplicate decision state while allowing a new completed candle to be recorded."""
    stable = {k: v for k, v in snapshot.items() if k != "timestamp"}
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def append_if_changed(snapshot: dict[str, Any], path: Path = AUDIT_JSONL) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous: dict[str, Any] | None = None
    if path.exists():
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            try:
                previous = json.loads(lines[-1])
            except (json.JSONDecodeError, TypeError):
                previous = None
    if previous is not None and _fingerprint(previous) == _fingerprint(snapshot):
        return False
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n")
    return True
