# VKCO ARCHITECTURE — R1.8

## Data flow
`GitHub Actions -> MOEX ISS -> strategy engines -> gates -> model lifecycle -> journals/audits -> public_status -> GitHub Pages / Telegram`

## Components
- `monitor.py`: S1 market data, adaptive setup detection, IMOEX/event-risk integration.
- `run_r18.py`: production orchestration.
- `position_manager.py`: model lifecycle; monotonic LONG-target safety invariant.
- `trade_journal.py`: immutable closed-trade evidence/statistics.
- `decision_audit.py`: deduplicated decision-state evidence.
- `strategy2_ema.py`: S2 shadow.
- `strategy3_value_rsi.py`: S3 shadow.
- `strategy4_h1.py`: S4 H1 shadow + structural S/R + MA50/MA200 context + independent audit.
- `fundamental_analysis.py`: official VK IR parser, fail-closed.
- `valuation.py`: read-only EV/EBITDA scenario valuation.
- `export_status.py`: sanitized browser contract.
- `web/vkco-dashboard/index.html`: Control Room.

## Boundaries
No broker API/orders. No DB/Redis/VPS/Docker/ML required. TradingView is a public iframe widget; RSI14 is embedded, MA50/MA200 are computed from completed MOEX H1 candles and displayed outside the iframe.

## Safety
Critical missing evidence -> WAIT/DATA_UNAVAILABLE, never fabricated READY. Strategy states are independent. Historical journal evidence is not rewritten.
