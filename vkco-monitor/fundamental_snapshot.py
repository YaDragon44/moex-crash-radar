from __future__ import annotations

from typing import Any
import requests

URL = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/VKCO.json"
COLUMNS = "SECID,SHORTNAME,LOTSIZE,ISSUESIZE,ISIN,LISTLEVEL"


def fetch_snapshot(price: float | None = None) -> dict[str, Any]:
    """Read-only issuer/security snapshot from MOEX ISS. Fail closed."""
    try:
        r = requests.get(
            URL,
            params={"iss.meta": "off", "iss.only": "securities", "securities.columns": COLUMNS},
            headers={"User-Agent": "VKCO-Monitor/1.8"},
            timeout=20,
        )
        r.raise_for_status()
        block = r.json().get("securities") or {}
        cols, rows = block.get("columns") or [], block.get("data") or []
        if not rows:
            raise ValueError("MOEX security profile is empty")
        item = dict(zip(cols, rows[0]))
        issue_size = int(item["ISSUESIZE"]) if item.get("ISSUESIZE") is not None else None
        market_cap = round(float(price) * issue_size, 2) if price is not None and issue_size else None
        return {
            "status": "OK",
            "source": "MOEX ISS",
            "secid": item.get("SECID"),
            "shortname": item.get("SHORTNAME"),
            "issue_size": issue_size,
            "lot_size": item.get("LOTSIZE"),
            "isin": item.get("ISIN"),
            "list_level": item.get("LISTLEVEL"),
            "market_cap_rub": market_cap,
            "market_cap_basis": "latest VKCO market price × MOEX issue size" if market_cap is not None else None,
        }
    except Exception as exc:
        return {"status": "DATA_UNAVAILABLE", "source": "MOEX ISS", "error": type(exc).__name__}
