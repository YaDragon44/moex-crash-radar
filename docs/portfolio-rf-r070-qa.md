# Portfolio RF R0.7 QA

Status: CANDIDATE

Simplicity gate:
- one production HTML file changed
- no backend
- no timers/polling
- no Decision Score
- no optimizer
- no auto-trading
- MOEX remains manual and fail-soft
- first render is static
- decision vocabulary is explicit

Decision rule: BUSINESS -> PRICE -> RISK -> ACTION.

Data rule: insufficient verified data must not become BUY/ADD. Use HOLD/WATCH as appropriate.
