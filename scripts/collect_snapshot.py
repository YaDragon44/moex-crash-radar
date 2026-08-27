from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from moex_crash_radar.engine import calculate_crash
from moex_crash_radar.features import derive_index_signals
from moex_crash_radar.moex import fetch_index_candles


def main() -> None:
    end = date.today()
    start = end - timedelta(days=500)
    candles = fetch_index_candles("IMOEX", start=start.isoformat(), end=end.isoformat())
    if not candles:
        raise SystemExit("MOEX returned no IMOEX candles")

    signals = derive_index_signals(candles)
    crash = calculate_crash(signals)
    payload = {
        "as_of": candles[-1].begin,
        "source": "MOEX ISS",
        "secid": "IMOEX",
        "last_close": candles[-1].close,
        "data_quality": crash.quality.value,
        "signals": {k: {"score": v.score, "quality": v.quality.value} for k, v in signals.items()},
        "crash": {
            "score": crash.score,
            "state": crash.state.value,
            "available_weight": round(crash.available_weight, 4),
            "critical_confirmations": crash.critical_confirmations,
            "cash_signal": crash.cash_signal,
        },
        "note": "Index-only evidence. Breadth, volume/distribution, rates, oil/RUB, macro and news are intentionally absent until sourced; DATA_INSUFFICIENT is expected when total usable weight is below 70%.",
    }

    out = Path("artifacts/market_snapshot.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
