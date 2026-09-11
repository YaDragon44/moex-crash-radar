# VKCO Monitor R1.0 Production

Минимальный облачный монитор без VPS и без включенного локального компьютера.

## Архитектура

GitHub Actions → MOEX ISS → `monitor.py` → Telegram Bot.

## Production scope

- реальные 10-минутные свечи `VKCO`, MOEX board `TQBR`;
- setup `Wyckoff Spring / False Breakout` в зоне 127–130 ₽;
- setup `Breakout + Hold` выше 141 ₽ (2 закрытия подряд);
- статусы `WAIT` / `READY` в логах;
- Telegram отправляется только при `READY`;
- anti-duplicate по `signal_id` через GitHub Actions cache;
- scheduled run каждые 10 минут в будни (UTC 06:00–20:59);
- stale-data gate: старые данные не дают сигнал;
- regression tests перед каждым production run;
- ручной режим `run` и `test_telegram`.

## GitHub Secrets (обязательный ручной шаг)

Repository → Settings → Secrets and variables → Actions → New repository secret:

1. `TELEGRAM_BOT_TOKEN` — новый токен BotFather, который никогда не публиковался.
2. `TELEGRAM_CHAT_ID` — ваш Telegram chat id.

Секреты не должны храниться в коде, issue, README или Actions logs.

## Production validation

После merge в `main`:

1. Actions → `VKCO Monitor R1.0` → Run workflow → `test_telegram`.
2. Ожидаемый Telegram: `✅ VKCO R1.0 Production: Telegram test OK`.
3. Run workflow → `run`.
4. В логах должен быть либо `status=WAIT ...`, либо `status=READY sent=1 ...`.
5. После этого scheduled workflow работает автоматически; локальный компьютер не нужен.

## Ограничения R1.0

- GitHub Actions не является real-time/HFT инфраструктурой; возможна задержка scheduled run.
- R1.0 предназначен для 10–15m/swing trigger monitoring.
- Полный 19-факторный Confluence не рассчитывается: факторы, которых нет в MVP, считаются нулём и это явно отмечено в Telegram.
- Новости/event-risk автоматически не блокируют вход; сообщение требует ручной проверки события перед сделкой.

## Безопасность

Монитор read-only к MOEX и имеет только право отправлять сообщения через Telegram Bot API. Доступа к брокерскому счёту и права совершать сделки нет.
