# Morning Dashboard → Make

Version: 1.0.0 · 2026-10-08

The morning workflow keeps its existing 08:00 Europe/Moscow schedule and Python data sources. Delivery uses Make scenario 7813123, branch `kind=morning_greeting`, when the repository secret `MAKE_API_TOKEN` is configured. Without that secret it keeps direct Telegram delivery. A Make failure never triggers fallback to Telegram because an uncertain run may already have sent the message.

## Configuration

1. In Make create an API token with permission to run scenarios for the organization containing team 2532147. Keep the token private.
2. Add it as GitHub Actions repository secret `MAKE_API_TOKEN`. This is a Make API token, not the Telegram bot token.
3. Keep `TELEGRAM_CHAT_ID` set to the intended morning recipients. Each comma-separated recipient is sent separately as `morning_chat_id`; the default recipient in Make is not substituted for these values.
4. Keep `TELEGRAM_BOT_TOKEN` for best-effort deletion of the previous message. It must refer to the same bot connected to the morning Make branch. Without it delivery still works, but old messages are retained.
5. Run Morning Dashboard MVP manually only when delivery is intended. A same-day confirmed delivery is skipped.

## Verification and recovery

`MORNING_DELIVERY transport=make` identifies the selected transport. `PASS personal-morning` requires successful execution, `status=sent`, matching chat_id, and a positive message_id. Unknown output layouts fail closed; production response layout still requires a live check.

The state cache persists a pending marker before the Make POST. A timeout does not retry or fall back. Inspect the same execution in Make: if delivery occurred, reconcile the cached state with its message_id and delivery date; if no message was sent, clear that recipient's pending marker only after checking the run, then retry. An unresolved pending marker blocks that recipient for the same Moscow date. Cache eviction or overlapping workflows outside the workflow concurrency group can still defeat this protection; this is not global exactly-once delivery.

Confirmed delivery is saved before deletion of the previous message. Data collection and the Make scheduler are not migrated in this release. Existing GitHub cron remains the only morning scheduler.

## References

- https://developers.make.com/api-documentation/api-reference/scenarios
- https://developers.make.com/api-documentation/authentication
- https://eu1.make.com/2532147/scenarios/7813123
