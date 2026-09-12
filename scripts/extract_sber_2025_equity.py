#!/usr/bin/env python3
"""R1.8.42 — extract traceable equity/share-basis evidence from Sber 2025 Annual Report PDF.

This script is deliberately non-semantic: it finds candidate passages with page numbers,
but never maps total equity to common equity and never marks the valuation VERIFIED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "attributable_equity": [
        r"принадлежащ\w*\s+акционер\w*",
        r"капитал\w*\s+акционер\w*",
        r"attributable\s+to\s+(?:the\s+)?shareholders",
    ],
    "treasury_shares": [
        r"собственн\w*\s+акци",
        r"выкупленн\w*\s+акци",
        r"казначейск\w*\s+акци",
        r"treasury\s+shares",
    ],
    "shares_outstanding": [
        r"акци\w*\s+в\s+обращени",
        r"находящ\w*\s+в\s+обращени",
        r"shares\s+outstanding",
    ],
    "ordinary_shares": [
        r"обыкновенн\w*\s+акци",
        r"ordinary\s+shares",
        r"common\s+shares",
    ],
    "preferred_shares": [
        r"привилегированн\w*\s+акци",
        r"preferred\s+shares",
    ],
    "liquidation_rights": [
        r"ликвидационн\w*\s+стоимост",
        r"liquidation\s+value",
        r"liquidation\s+preference",
    ],
}


def pdf_pages(pdf: Path) -> int:
    out = subprocess.check_output(["pdfinfo", str(pdf)], text=True, errors="replace")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        raise RuntimeError("pdfinfo did not return page count")
    return int(m.group(1))


def page_text(pdf: Path, page: int) -> str:
    return subprocess.check_output(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        text=True,
        errors="replace",
    )


def normalize_line(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract(pdf: Path) -> dict:
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    pages = pdf_pages(pdf)
    matches = []
    compiled = {k: [re.compile(p, re.I) for p in ps] for k, ps in PATTERNS.items()}

    for page in range(1, pages + 1):
        text = page_text(pdf, page)
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            if not line.strip():
                continue
            for category, regexes in compiled.items():
                if any(rx.search(line) for rx in regexes):
                    lo, hi = max(0, idx - 2), min(len(lines), idx + 3)
                    context = " | ".join(normalize_line(x) for x in lines[lo:hi] if x.strip())
                    matches.append({
                        "category": category,
                        "page": page,
                        "line": idx + 1,
                        "locator": f"page:{page}:line:{idx+1}",
                        "context": context[:1200],
                    })
                    break

    counts = {k: 0 for k in PATTERNS}
    for m in matches:
        counts[m["category"]] += 1

    return {
        "status": "CANDIDATES_EXTRACTED" if matches else "NO_CANDIDATES",
        "document_sha256": digest,
        "pages": pages,
        "candidate_counts": counts,
        "matches": matches,
        "semantic_verification": False,
        "valuation_gate": "PARTIAL",
        "warning": "Candidate passages only. Do not infer attributable common equity, shares outstanding or preferred-share treatment without field-level review.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = extract(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "document_sha256", "pages", "candidate_counts", "semantic_verification", "valuation_gate")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
