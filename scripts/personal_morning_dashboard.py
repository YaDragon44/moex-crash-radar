from __future__ import annotations

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import requests

MSK = ZoneInfo("Europe/Moscow")
MOSCOW = (55.7558, 37.6176)
NAKHIMOVSKY = (55.6626, 37.6055)
GISMETEO_MOSCOW_DAY = "https://www.gismeteo.ru/weather-moscow-4368/"


def get_json(url: str, params=None):
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "morning-dashboard/1.0"})
    r.raise_for_status()
    return r.json()


def telegram_send(token: str, chat_id: str, text: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": "false"},
        timeout=30,
    )
    r.raise_for_status()


def parse_chat_ids(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def weather_block() -> str:
    lat, lon = MOSCOW
    data = get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "timezone": "Europe/Moscow",
            "current": "temperature_2m,precipitation,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "wind_speed_unit": "ms",
            "forecast_days": 1,
        },
    )
    cur = data["current"]
    day = data["daily"]

    nlat, nlon = NAKHIMOVSKY
    hourly = get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": nlat,
            "longitude": nlon,
            "timezone": "Europe/Moscow",
            "hourly": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m",
            "wind_speed_unit": "ms",
            "forecast_days": 1,
        },
    )
    today = datetime.now(MSK).strftime("%Y-%m-%d")
    target = f"{today}T08:00"
    try:
        i = hourly["hourly"]["time"].index(target)
    except ValueError:
        i = 8
    h = hourly["hourly"]

    t_now = round(cur["temperature_2m"])
    t_min = round(day["temperature_2m_min"][0])
    t_max = round(day["temperature_2m_max"][0])
    pop = day["precipitation_probability_max"][0]
    wind = cur["wind_speed_10m"]
    nt = round(h["temperature_2m"][i])
    feels = round(h["apparent_temperature"][i])
    rain = h["precipitation"][i]
    nwind = h["wind_speed_10m"][i]

    if t_max <= 12:
        clothes = "куртка/ветровка, закрытая обувь"
    elif t_min <= 12:
        clothes = "лёгкая куртка утром, днём можно снять"
    elif pop and pop >= 50:
        clothes = "лёгкий слой + компактный зонт"
    else:
        clothes = "футболка/рубашка, лёгкий верх на утро"

    return (
        "🌤 ПОГОДА · МОСКВА\n"
        f"🌡 Сейчас  {t_now:+d}°   ↕️ день {t_min:+d}…{t_max:+d}°\n"
        f"🌧 Осадки  {pop}%   💨 ветер {wind:.1f} м/с\n"
        "\n"
        "📍 Нахимовский · ~08:00\n"
        f"🌡 {nt:+d}° · ощущается {feels:+d}°\n"
        f"🌧 {rain:g} мм   💨 {nwind:.1f} м/с\n"
        f"👕 {clothes}\n"
        "🙂 Утренний гардероб снова работает по схеме «слой снял — слой понёс»."
    )


def usd_rub() -> tuple[str, str]:
    r = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=30, headers={"User-Agent": "morning-dashboard/1.0"})
    r.raise_for_status()
    root = ET.fromstring(r.content)
    date = root.attrib.get("Date", "")
    for valute in root.findall("Valute"):
        if valute.findtext("CharCode") == "USD":
            nominal = float(valute.findtext("Nominal", "1").replace(",", "."))
            value = float(valute.findtext("Value", "0").replace(",", ".")) / nominal
            return f"{value:.4f} ₽", f"ЦБ РФ {date}"
    raise RuntimeError("USD not found in CBR XML")


def btc_usd() -> tuple[str, str]:
    data = get_json("https://api.coinbase.com/v2/prices/BTC-USD/spot")
    value = float(data["data"]["amount"])
    return f"${value:,.0f}", "Coinbase spot"


def sberp_close() -> tuple[str, str]:
    today = datetime.now(MSK).date()
    start = today - timedelta(days=14)
    data = get_json(
        "https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/SBERP.json",
        {"from": start.isoformat(), "till": today.isoformat(), "iss.meta": "off"},
    )
    hist = data["history"]
    cols = hist["columns"]
    rows = hist["data"]
    idx_date = cols.index("TRADEDATE")
    idx_close = cols.index("CLOSE")
    valid = [(r[idx_date], r[idx_close]) for r in rows if r[idx_close] is not None]
    if not valid:
        raise RuntimeError("Official SBERP CLOSE unavailable")
    trade_date, close = valid[-1]
    dt = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    return f"{float(close):.2f} ₽", f"ПОСЛЕДНЕЕ ЗАКРЫТИЕ · {dt} · MOEX ISS"


def finance_block() -> str:
    try:
        usd, usd_src = usd_rub()
    except Exception:
        usd, usd_src = "N/A", "ЦБ РФ: данные недоступны"
    try:
        btc, btc_src = btc_usd()
    except Exception:
        btc, btc_src = "N/A", "BTC: данные недоступны"
    try:
        sber, sber_src = sberp_close()
    except Exception:
        sber, sber_src = "N/A", "MOEX: официальный CLOSE недоступен"

    stamp = datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")
    return (
        "💰 ФИНАНСЫ\n"
        f"💵 USD/RUB  {usd}\n"
        f"₿ BTC/USD   {btc}\n"
        f"🏦 SBERP     {sber}\n"
        f"   {sber_src}\n"
        "\n"
        f"🕒 {stamp}\n"
        f"Источники: {usd_src}; {btc_src}\n"
        "🙂 Bitcoin работает без выходных. Сбер хотя бы умеет выключать терминал."
    )


def gismeteo_block() -> str:
    return (
        "🌦 GISMETEO · МОСКВА · НА ДЕНЬ\n"
        f"{GISMETEO_MOSCOW_DAY}"
    )


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    raw_ids = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not raw_ids:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    text = weather_block() + "\n\n" + finance_block() + "\n\n" + gismeteo_block()
    failures = 0
    for chat_id in parse_chat_ids(raw_ids):
        try:
            telegram_send(token, chat_id, text)
            print(f"PASS personal-morning recipient={chat_id}")
        except Exception as exc:
            failures += 1
            print(f"FAIL personal-morning recipient={chat_id}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
