from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import requests

MSK = ZoneInfo("Europe/Moscow")
ZYUZINO = (55.6557, 37.5763)


WEEKDAYS_RU = ("ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ")
MONTHS_RU = ("", "ЯНВАРЯ", "ФЕВРАЛЯ", "МАРТА", "АПРЕЛЯ", "МАЯ", "ИЮНЯ", "ИЮЛЯ", "АВГУСТА", "СЕНТЯБРЯ", "ОКТЯБРЯ", "НОЯБРЯ", "ДЕКАБРЯ")
SYNODIC_MONTH = 29.530588853
# Reference new moon: 2000-01-06 18:14 UTC (Meeus-style epoch approximation).
NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=ZoneInfo("UTC"))


def morning_header(now: datetime | None = None) -> str:
    now = now or datetime.now(MSK)
    utc_now = now.astimezone(ZoneInfo("UTC"))
    age = ((utc_now - NEW_MOON_EPOCH).total_seconds() / 86400.0) % SYNODIC_MONTH
    lunar_day = min(30, int(age) + 1)
    waxing = age < (SYNODIC_MONTH / 2)
    phase = "🌒 растущая" if waxing else "🌘 убывающая"
    return (
        f"📅 {WEEKDAYS_RU[now.weekday()]} · {now.day} {MONTHS_RU[now.month]} {now.year}\n"
        f"🌙 Луна: {lunar_day}-е лунные сутки · {phase}"
    )


def get_json(url: str, params=None):
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "morning-dashboard/1.0"})
    r.raise_for_status()
    return r.json()


def telegram_send(token: str, chat_id: str, text: str) -> int:
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, timeout=30)
    r.raise_for_status()
    return int(r.json()["result"]["message_id"])


def telegram_delete(token: str, chat_id: str, message_id: int) -> None:
    r = requests.post(f"https://api.telegram.org/bot{token}/deleteMessage",
                      data={"chat_id": chat_id, "message_id": message_id}, timeout=30)
    r.raise_for_status()


def parse_chat_ids(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def rain_timing(hourly: dict) -> str:
    times = hourly["time"]
    probs = hourly.get("precipitation_probability", [])
    amounts = hourly.get("precipitation", [])
    wet = []
    for i, ts in enumerate(times):
        prob = probs[i] if i < len(probs) and probs[i] is not None else 0
        amount = amounts[i] if i < len(amounts) and amounts[i] is not None else 0
        if prob >= 30 or amount > 0:
            wet.append((i, datetime.fromisoformat(ts).hour, prob, amount))
    if not wet:
        return "☔ Дождь: существенных осадков по часам не ожидается"

    groups = []
    start = prev = wet[0][0]
    for item in wet[1:]:
        idx = item[0]
        if idx == prev + 1:
            prev = idx
        else:
            groups.append((start, prev))
            start = prev = idx
    groups.append((start, prev))

    parts = []
    for start, end in groups[:3]:
        h1 = datetime.fromisoformat(times[start]).hour
        h2 = (datetime.fromisoformat(times[end]).hour + 1) % 24
        max_prob = max((probs[i] or 0) for i in range(start, end + 1))
        total_mm = sum((amounts[i] or 0) for i in range(start, end + 1))
        parts.append(f"{h1:02d}:00–{h2:02d}:00 до {max_prob:.0f}% (~{total_mm:.1f} мм)")
    return "☔ Дождь: " + "; ".join(parts)


def weather_block() -> str:
    lat, lon = ZYUZINO
    base_params = {
        "latitude": lat, "longitude": lon, "timezone": "Europe/Moscow",
        "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
        "hourly": "precipitation_probability,precipitation",
        "wind_speed_unit": "ms", "forecast_days": 10,
    }
    data = get_json("https://api.open-meteo.com/v1/forecast", base_params)
    model_daily = {}
    for model in ("ecmwf_ifs025", "gfs_seamless", "icon_seamless"):
        try:
            params = dict(base_params); params["models"] = model
            model_daily[model] = get_json("https://api.open-meteo.com/v1/forecast", params)["daily"]
            md = model_daily[model]
            print("WEATHER_MODEL", model, list(zip(md["time"], md["temperature_2m_min"], md["temperature_2m_max"], md["precipitation_probability_max"], md["precipitation_sum"])))
        except Exception as exc:
            print(f"WARN weather-model {model}: {exc}")
    cur, day = data["current"], data["daily"]
    rain_line = rain_timing(data["hourly"])
    t_now = round(cur["temperature_2m"]); feels = round(cur["apparent_temperature"])
    t_min = round(day["temperature_2m_min"][0]); t_max = round(day["temperature_2m_max"][0])
    pop = day["precipitation_probability_max"][0] or 0; wind = cur["wind_speed_10m"]

    if t_max <= 12: clothes = "куртка/ветровка, закрытая обувь"
    elif t_min <= 12: clothes = "лёгкая куртка утром, днём можно снять"
    elif pop >= 50: clothes = "лёгкий слой + компактный зонт"
    else: clothes = "футболка/рубашка, лёгкий верх на утро"

    ru_days = ("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")
    forecast = []
    for idx, (dt, lo, hi, probability, mm) in enumerate(zip(
        day["time"], day["temperature_2m_min"], day["temperature_2m_max"],
        day["precipitation_probability_max"], day["precipitation_sum"]
    )):
        d = datetime.fromisoformat(dt)
        highs = [m["temperature_2m_max"][idx] for m in model_daily.values() if idx < len(m["temperature_2m_max"]) and m["temperature_2m_max"][idx] is not None]
        spread = (max(highs) - min(highs)) if len(highs) >= 2 else None
        confidence = "🟢" if spread is not None and spread <= 2 else ("🟡" if spread is not None and spread <= 4 else "🔴")
        forecast.append(f"{ru_days[d.weekday()]} {round(lo):+d}…{round(hi):+d}° · 🌧{round(probability or 0):d}% · 💧{float(mm or 0):.1f} мм {confidence}")

    return (
        "🌤 ЗЮЗИНО · МОСКВА\n"
        f"🌡 Сейчас {t_now:+d}° · ощущается {feels:+d}° · день {t_min:+d}…{t_max:+d}°\n"
        f"🌧 Осадки до {pop:.0f}% · 💨 ветер {wind:.1f} м/с\n"
        f"{rain_line}\n"
        f"👕 {clothes}\n\n"
        "📆 ПРОГНОЗ НА 10 ДНЕЙ\n" + "\n".join(forecast) + "\n🟢 модели близки · 🟡 расходятся · 🔴 высокая неопределённость"
    )

def usd_rub() -> tuple[str, str]:
    r = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=30, headers={"User-Agent": "morning-dashboard/1.0"}); r.raise_for_status(); root = ET.fromstring(r.content); date = root.attrib.get("Date", "")
    for valute in root.findall("Valute"):
        if valute.findtext("CharCode") == "USD":
            nominal = float(valute.findtext("Nominal", "1").replace(",", ".")); value = float(valute.findtext("Value", "0").replace(",", ".")) / nominal
            return f"{value:.4f} ₽", f"ЦБ РФ {date}"
    raise RuntimeError("USD not found in CBR XML")


def crypto_usd(symbol: str, decimals: int) -> tuple[str, str]:
    # Primary: Coinbase spot. Cross-check against Kraken ticker on every run.
    started = datetime.now(ZoneInfo("UTC"))
    cb = get_json(f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot")
    cb_price = float(cb["data"]["amount"])
    pair = "XBTUSD" if symbol == "BTC" else "ETHUSD"
    kr = get_json("https://api.kraken.com/0/public/Ticker", {"pair": pair})
    if kr.get("error"):
        raise RuntimeError(f"Kraken {symbol} validation failed: {kr['error']}")
    row = next(iter(kr["result"].values()))
    kr_price = float(row["c"][0])
    deviation = abs(cb_price - kr_price) / ((cb_price + kr_price) / 2)
    if deviation > 0.005:
        raise RuntimeError(f"{symbol} source divergence {deviation:.2%}")
    checked = datetime.now(MSK)
    if (datetime.now(ZoneInfo("UTC")) - started).total_seconds() > 60:
        raise RuntimeError(f"{symbol} quote validation stale")
    return f"${cb_price:,.{decimals}f}", f"Coinbase spot + Kraken check {checked:%H:%M:%S} МСК"


def btc_usd() -> tuple[str, str]:
    return crypto_usd("BTC", 0)


def eth_usd() -> tuple[str, str]:
    return crypto_usd("ETH", 2)


def moex_close(secid: str) -> tuple[str, str]:
    today = datetime.now(MSK).date(); start = today - timedelta(days=14)
    data = get_json(f"https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/{secid}.json", {"from": start.isoformat(), "till": today.isoformat(), "iss.meta": "off"})
    hist = data["history"]; cols = hist["columns"]; rows = hist["data"]; idx_date = cols.index("TRADEDATE"); idx_close = cols.index("CLOSE")
    valid = [(r[idx_date], r[idx_close]) for r in rows if r[idx_close] is not None]
    if not valid: raise RuntimeError(f"Official {secid} CLOSE unavailable")
    trade_date, close = valid[-1]; dt = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    return f"{float(close):.2f} ₽", f"ПОСЛЕДНЕЕ ЗАКРЫТИЕ · {dt} · MOEX ISS"


def finance_block() -> str:
    try: usd, usd_src = usd_rub()
    except Exception: usd, usd_src = "N/A", "ЦБ РФ: данные недоступны"
    try: btc, btc_src = btc_usd()
    except Exception: btc, btc_src = "N/A", "BTC: данные недоступны"
    try: eth, eth_src = eth_usd()
    except Exception: eth, eth_src = "N/A", "ETH/USD: данные недоступны"
    try: sber, sber_src = moex_close("SBERP")
    except Exception: sber, sber_src = "N/A", "MOEX: официальный SBERP CLOSE недоступен"
    try: vkco, vkco_src = moex_close("VKCO")
    except Exception: vkco, vkco_src = "N/A", "MOEX: официальный VKCO CLOSE недоступен"
    stamp = datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")
    return ("💰 ФИНАНСЫ\n" f"USD/RUB   {usd}\n" f"BTC/USD   {btc}   -   ETH/USD   {eth}\n" f"SBERP     {sber}   -   VKCO      {vkco}\n" f"ПОСЛЕДНЕЕ ЗАКРЫТИЕ · {sber_src.split(' · ')[1] if ' · ' in sber_src else 'дата недоступна'} · MOEX ISS\n\n" f"🕒 {stamp}\n" f"Источники: {usd_src}; {btc_src}; {eth_src}\n" "🙂 Bitcoin работает без выходных. Сбер хотя бы умеет выключать терминал.")


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN"); raw_ids = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not raw_ids: raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    text = morning_header() + "\n\n" + weather_block() + "\n\n" + finance_block(); failures = 0
    state_path = "artifacts/morning_dashboard_state.json"
    try:
        with open(state_path, "r", encoding="utf-8") as fh: state = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    for chat_id in parse_chat_ids(raw_ids):
        try:
            old_id = state.get(chat_id)
            if old_id:
                try:
                    telegram_delete(token, chat_id, int(old_id))
                    print(f"PASS delete-previous recipient={chat_id}")
                except Exception as exc:
                    print(f"WARN delete-previous recipient={chat_id}: {exc}")
            new_id = telegram_send(token, chat_id, text)
            state[chat_id] = new_id
            print(f"PASS personal-morning recipient={chat_id}")
        except Exception as exc:
            failures += 1; print(f"FAIL personal-morning recipient={chat_id}: {exc}")
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as fh: json.dump(state, fh)
    return 1 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
