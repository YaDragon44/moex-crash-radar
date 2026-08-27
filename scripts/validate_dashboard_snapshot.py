from __future__ import annotations

import json
from pathlib import Path

from moex_crash_radar.dashboard_contract import assert_dashboard_snapshot


def main() -> None:
    path = Path("artifacts/market_snapshot.json")
    if not path.exists():
        raise SystemExit("market snapshot not found")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    assert_dashboard_snapshot(snapshot)
    print("R0.4.1 dashboard contract: PASS")


if __name__ == "__main__":
    main()
