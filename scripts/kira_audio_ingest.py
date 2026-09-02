#!/usr/bin/env python3
"""Offline/CI-safe Kira transcript ingest.

Input is an ASR JSON file. This deliberately does not scrape Telegram or YouTube;
media acquisition is a separate authorized adapter. Output can be audited before
writing portfolio changes to storage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from moex_crash_radar.kira_audio_parser import TranscriptSegment, parse_transcript, serialize


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript", type=Path, help="JSON: {segments:[{start,end,text}, ...]}")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    payload = json.loads(args.transcript.read_text(encoding="utf-8"))
    segments = [TranscriptSegment(float(x["start"]), float(x["end"]), str(x["text"])) for x in payload["segments"]]
    result = {
        "source_url": args.source_url,
        "segment_count": len(segments),
        "changes": serialize(parse_transcript(segments, args.source_url)),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
