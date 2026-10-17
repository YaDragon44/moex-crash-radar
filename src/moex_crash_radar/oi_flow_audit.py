from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .futoi import FutoiPair, pair_snapshots, parse_futoi_rows, is_point_in_time_safe

ISS_BASE = "https://iss.moex.com/iss"


@dataclass(frozen=True)
class CoverageResult:
    ticker: str
    start: str
    end: str
    rows: int
    paired_snapshots: int
    unique_days: int
    first_moment: str | None
    last_moment: str | None
    point_in_time_violations: int
    status: str
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def _get_json(url: str, timeout: int = 30) -> dict:
    req = Request(url, headers={"User-Agent": "moex-crash-radar/1.3.1"})
    with urlopen(req, timeout=timeout) as response:  # nosec B310: fixed HTTPS MOEX endpoint
        return json.loads(response.read().decode("utf-8"))


def _extract_rows(payload: dict) -> list[dict]:
    # Historical FUTOI responses have used different block names over time.
    # Detect the block by required columns instead of relying on a single name.
    required = {"TICKER", "CLGROUP", "POS", "POS_LONG", "POS_SHORT", "MOMENT", "SYSTIME"}
    for block in payload.values():
        if not isinstance(block, dict):
            continue
        columns = block.get("columns")
        data = block.get("data")
        if not isinstance(columns, list) or not isinstance(data, list):
            continue
        normalized = {str(c).upper() for c in columns}
        if required.issubset(normalized):
            cols = [str(c).upper() for c in columns]
            return [dict(zip(cols, row)) for row in data]
    return []


def fetch_futoi_history(ticker: str, *, start: str, end: str, max_pages: int = 100) -> list[dict]:
    """Fetch delayed/public historical FUTOI without fabricating missing rows.

    MOEX limits historical FUTOI responses; pagination is performed with `start`.
    The endpoint is expected to expose historical data with a publication delay for
    unauthenticated users. This function is for research/backtest data only.
    """
    ticker = ticker.lower()
    rows: list[dict] = []
    offset = 0
    for _ in range(max_pages):
        params = {"from": start, "till": end, "start": offset, "iss.meta": "off"}
        url = f"{ISS_BASE}/analyticalproducts/futoi/securities/{ticker}.json?{urlencode(params)}"
        payload = _get_json(url)
        batch = _extract_rows(payload)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += len(batch)
    return rows


def audit_futoi_history(ticker: str, *, start: str, end: str) -> CoverageResult:
    rows = fetch_futoi_history(ticker, start=start, end=end)
    snapshots = parse_futoi_rows(rows)
    pairs = pair_snapshots(snapshots)
    moments = [p.moment for p in pairs]
    days = {m[:10] for m in moments if len(m) >= 10}

    violations = 0
    for pair in pairs:
        # A backtest decision cannot use a snapshot before MOEX published it.
        # Use each pair's own latest publication time as the earliest safe decision.
        decision = max(pair.retail.systime, pair.legal.systime)
        if not is_point_in_time_safe(pair, decision):
            violations += 1

    if not rows:
        status = "N/A"
        note = "No historical FUTOI rows returned for requested range/ticker."
    elif not pairs:
        status = "FAIL"
        note = "Rows exist but FIZ/YUR snapshots cannot be paired by timestamp."
    elif violations:
        status = "FAIL"
        note = "Publication timestamp integrity violation detected."
    else:
        status = "READY"
        note = "Historical FIZ/YUR pairs available; use SYSTIME as availability timestamp."

    return CoverageResult(
        ticker=ticker.upper(),
        start=start,
        end=end,
        rows=len(rows),
        paired_snapshots=len(pairs),
        unique_days=len(days),
        first_moment=min(moments) if moments else None,
        last_moment=max(moments) if moments else None,
        point_in_time_violations=violations,
        status=status,
        note=note,
    )


def public_safe_end(now: datetime | None = None, delay_days: int = 15) -> str:
    """Latest date that should be expected from delayed unauthenticated FUTOI."""
    current = now or datetime.now(timezone.utc)
    return (current.date() - timedelta(days=delay_days)).isoformat()
