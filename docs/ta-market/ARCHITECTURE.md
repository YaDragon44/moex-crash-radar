# TA Market Monitor — Architecture

## Principle
Keep the production path static, deterministic and fail-closed.

## E2E
MOEX ISS
  -> scripts/collect_ta_market_snapshot.py
  -> artifacts/ta_market/current.json
  -> scripts/update_ta_signal_history.py
  -> artifacts/ta_market/signal_history.json
  -> scripts/evaluate_ta_signal_performance.py
  -> artifacts/ta_market/signal_performance.json
  -> scripts/prepare_ta_ready_alert.py
  -> Telegram notification for new READY only
  -> GitHub Pages
  -> web/ta-market/

## Scheduling
The TA snapshot workflow runs on weekdays during the configured Moscow-market window and can also be dispatched manually. It validates production contracts before persisting state and dispatching Pages.

## Runtime artifacts
- current.json — latest market snapshot and context.
- signal_history.json — deduplicated state transitions.
- signal_performance.json — READY outcome statistics and Sample Quality.
- telegram_state.json — alert baseline/deduplication state.

## Safety boundaries
- Browser does not call MOEX directly.
- Snapshot and context quality are validated before public deployment.
- READY is fail-closed.
- The same persisted snapshot must produce deterministic history analysis; R0.9.2.3 anchors analysis time to snapshot.generated_at.
- Public Pages health checks validate JSON, history, performance, safety/risk/observation UI markers.

## Simplicity rule
No dedicated backend is required for this monitor. Do not add infrastructure or indicators unless an observed production problem or evidence review requires it.
