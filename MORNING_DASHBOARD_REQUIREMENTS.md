# MORNING DASHBOARD — CANONICAL REQUIREMENTS

Status: ACTIVE BASELINE
Date: 2026-09-27
Timezone: Europe/Moscow (MSK)

## 1. Purpose

Deliver one compact, current morning Telegram dashboard. The user-facing message contains only:
1. date + factual lunar header;
2. Zyuzino weather + 10-day forecast;
3. finance.

No astrology interpretation, numerology, motivation, greeting, “energy/focus of day”, or “main idea of the day”.

## 2. Telegram delivery

- Target schedule: daily 08:01 MSK.
- A nearby fallback run may exist for scheduler reliability.
- There must be only ONE current user-facing morning dashboard per recipient.
- Before publishing a new dashboard, delete the previously stored morning-dashboard message via its Telegram message_id.
- Store message_id separately for each recipient across workflow runs.
- If deletion fails, log WARN and still publish the fresh dashboard.
- Never expose bot token or recipient IDs.
- Do not send technical success/failure summaries to Telegram.
- Do not send MOEX Crash Radar screenshots, links, or Morning Dashboard Agent status messages as part of this delivery.
- Smoke-test triggers are diagnostic only and must use the same user-facing dashboard format.

## 3. Header

Every dashboard begins with:
```
📅 <DAY OF WEEK> · <DD MONTH YYYY>
🌙 Луна: <lunar day> · <waxing/waning>
```

Rules:
- Russian weekday and month names.
- Lunar information is factual only; no interpretation.
- Do not use a static placeholder.

## 4. Weather — Zyuzino only

Primary weather location: Zyuzino, Moscow.

Do NOT show a second Nakhimovsky weather block.
Do NOT send a Gismeteo webpage screenshot, ad-filled preview, or separate weather image.

Current/day block:
```
🌤 ЗЮЗИНО · МОСКВА
🌡 Сейчас <temp> · ощущается <temp> · день <min>…<max>
🌧 Осадки до <probability>% · 💨 ветер <speed> м/с
☔ Дождь: <hourly timing / no material rain>
👕 <short clothing recommendation>
```

Weather source:
- Open-Meteo is the canonical source.
- Temperature, precipitation probability, precipitation amount, wind and 10-day forecast must come from the same current Open-Meteo dataset/update.
- Never invent unavailable metrics.

## 5. Ten-day forecast

Immediately after the current Zyuzino block:
```
📆 ПРОГНОЗ НА 10 ДНЕЙ
<weekday> <min>…<max>° · 🌧<probability>% · 💧<precipitation> мм
...
```

Rules:
- 10 calendar forecast days including weekends.
- Each row: weekday, min/max, precipitation probability, precipitation amount in mm.
- Source: same Open-Meteo request/source family as the current block.

## 6. Finance

Required instruments:
- USD/RUB
- BTC/USD
- ETH/USD
- SBERP
- VKCO

Canonical visual layout:
```
💰 ФИНАНСЫ
USD/RUB   <value> ₽
BTC/USD   $<value>   -   ETH/USD   $<value>
SBERP     <value> ₽   -   VKCO      <value> ₽
ПОСЛЕДНЕЕ ЗАКРЫТИЕ · <DD.MM.YYYY> · MOEX ISS
```

Rules:
- No emoji/image before individual instruments.
- BTC and ETH are on one line.
- SBERP and VKCO are on one line.
- “ПОСЛЕДНЕЕ ЗАКРЫТИЕ” appears once, after the last MOEX security.
- On weekends/holidays use official CLOSE from the last completed MOEX session, with date.
- Never label an intraday/last trade as CLOSE.
- If official CLOSE is unavailable, state that truthfully.

Canonical sources:
- USD/RUB: Bank of Russia.
- BTC/USD: Coinbase spot.
- ETH/USD: Coinbase spot.
- SBERP/VKCO: MOEX ISS official history/CLOSE.

## 7. Footer

May contain:
- update timestamp in MSK;
- compact source attribution;
- one short natural finance/weather joke.

Footer must remain subordinate and compact.

## 8. Explicit exclusions / regression guards

The morning Telegram delivery MUST NOT reintroduce:
- generic “Москва” as the primary weather location instead of Zyuzino;
- Nakhimovsky duplicate weather block;
- Gismeteo screenshots or webpage previews;
- separate MOEX Crash Radar delivery;
- Morning Dashboard Agent “Успешно/Ошибок” messages;
- duplicate morning dashboards;
- placeholders such as $... or $x,xxx in actual/user-facing output;
- Binance ETH/USDT in place of canonical Coinbase ETH/USD;
- multiple “ПОСЛЕДНЕЕ ЗАКРЫТИЕ” lines.

## 9. Acceptance criteria

PASS only when:
1. fresh dashboard is successfully delivered to every configured recipient;
2. only one current morning dashboard remains per recipient after replacement logic has state;
3. header/date/lunar state are generated dynamically;
4. weather is Zyuzino + 10-day Open-Meteo forecast;
5. finance contains fresh USD/RUB, BTC/USD, ETH/USD and truthful SBERP/VKCO close data;
6. no excluded legacy/technical messages are sent.
