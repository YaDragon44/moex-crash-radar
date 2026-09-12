from __future__ import annotations

import monitor
from trade_plan import format_trade_plan

_original_format_signal = monitor.format_signal


def _format_signal_r14(signal):
    base = _original_format_signal(signal)
    return base + "\n\n💼 TRADE PLAN\n" + format_trade_plan(signal) + "\n\nДЕЙСТВИЕ: вход только по READY; стоп не расширять."


monitor.format_signal = _format_signal_r14

if __name__ == "__main__":
    raise SystemExit(monitor.run())
