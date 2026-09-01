from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
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


def telegram_send(token: str, chat_id: str, text: str, preview: bool = False) -> None:
    payload = {"chat_id": chat_id, "text": text}
    if preview:
        payload["link_preview_options"] = '{"is_disabled":false,"url":"' + GISMETEO_MOSCOW_DAY + '","prefer_large_media":true,"show_above_text":false}'
    else:
        payload["disable_web_page_preview"] = "true"
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, timeout=30)
    r.raise_for_status()


def telegram_send_photo(token: str, chat_id: str, image_path: Path, caption: str) -> None:
    with image_path.open("rb") as fh:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", data={"chat_id": chat_id, "caption": caption}, files={"photo": fh}, timeout=60)
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
    lat, lon = MOSCOW
    data = get_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "timezone": "Europe/Moscow",
        "current": "temperature_2m,precipitation,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "hourly": "precipitation_probability,precipitation",
        "wind_speed_unit": "ms", "forecast_days": 1,
    })
    cur, day = data["current"], data["daily"]
    rain_line = rain_timing(data["hourly"])

    nlat, nlon = NAKHIMOVSKY
    hourly = get_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": nlat, "longitude": nlon, "timezone": "Europe/Moscow",
        "hourly": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m",
        "wind_speed_unit": "ms", "forecast_days": 1,
    })
    target = f"{datetime.now(MSK).strftime('%Y-%m-%d')}T08:00"
    try: i = hourly["hourly"]["time"].index(target)
    except ValueError: i = 8
    h = hourly["hourly"]

    t_now = round(cur["temperature_2m"]); t_min = round(day["temperature_2m_min"][0]); t_max = round(day["temperature_2m_max"][0])
    pop = day["precipitation_probability_max"][0]; wind = cur["wind_speed_10m"]
    nt = round(h["temperature_2m"][i]); feels = round(h["apparent_temperature"][i]); rain = h["precipitation"][i]; nwind = h["wind_speed_10m"][i]

    if t_max <= 12: clothes = "куртка/ветровка, закрытая обувь"
    elif t_min <= 12: clothes = "лёгкая куртка утром, днём можно снять"
    elif pop and pop >= 50: clothes = "лёгкий слой + компактный зонт"
    else: clothes = "футболка/рубашка, лёгкий верх на утро"

    return (
        "🌤 ПОГОДА · МОСКВА\n"
        f"🌡 Сейчас  {t_now:+d}°   ↕️ день {t_min:+d}…{t_max:+d}°\n"
        f"🌧 Осадки  до {pop}%   💨 ветер {wind:.1f} м/с\n"
        f"{rain_line}\n\n"
        "📍 Нахимовский · ~08:00\n"
        f"🌡 {nt:+d}° · ощущается {feels:+d}°\n"
        f"🌧 {rain:g} мм   💨 {nwind:.1f} м/с\n"
        f"👕 {clothes}\n"
        "🙂 Утренний гардероб снова работает по схеме «слой снял — слой понёс»."
    )


def usd_rub() -> tuple[str, str]:
    r = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=30, headers={"User-Agent": "morning-dashboard/1.0"}); r.raise_for_status(); root = ET.fromstring(r.content); date = root.attrib.get("Date", "")
    for valute in root.findall("Valute"):
        if valute.findtext("CharCode") == "USD":
            nominal = float(valute.findtext("Nominal", "1").replace(",", ".")); value = float(valute.findtext("Value", "0").replace(",", ".")) / nominal
            return f"{value:.4f} ₽", f"ЦБ РФ {date}"
    raise RuntimeError("USD not found in CBR XML")


def btc_usd() -> tuple[str, str]:
    data = get_json("https://api.coinbase.com/v2/prices/BTC-USD/spot"); return f"${float(data['data']['amount']):,.0f}", "Coinbase spot"


def sberp_close() -> tuple[str, str]:
    today = datetime.now(MSK).date(); start = today - timedelta(days=14)
    data = get_json("https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/SBERP.json", {"from": start.isoformat(), "till": today.isoformat(), "iss.meta": "off"})
    hist = data["history"]; cols = hist["columns"]; rows = hist["data"]; idx_date = cols.index("TRADEDATE"); idx_close = cols.index("CLOSE")
    valid = [(r[idx_date], r[idx_close]) for r in rows if r[idx_close] is not None]
    if not valid: raise RuntimeError("Official SBERP CLOSE unavailable")
    trade_date, close = valid[-1]; dt = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    return f"{float(close):.2f} ₽", f"ПОСЛЕДНЕЕ ЗАКРЫТИЕ · {dt} · MOEX ISS"


def finance_block() -> str:
    try: usd, usd_src = usd_rub()
    except Exception: usd, usd_src = "N/A", "ЦБ РФ: данные недоступны"
    try: btc, btc_src = btc_usd()
    except Exception: btc, btc_src = "N/A", "BTC: данные недоступны"
    try: sber, sber_src = sberp_close()
    except Exception: sber, sber_src = "N/A", "MOEX: официальный CLOSE недоступен"
    stamp = datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")
    return ("💰 ФИНАНСЫ\n" f"💵 USD/RUB  {usd}\n" f"₿ BTC/USD   {btc}\n" f"🏦 SBERP     {sber}\n" f"   {sber_src}\n\n" f"🕒 {stamp}\n" f"Источники: {usd_src}; {btc_src}\n" "🙂 Bitcoin работает без выходных. Сбер хотя бы умеет выключать терминал.")


def make_gismeteo_card() -> Path:
    from playwright.sync_api import sync_playwright
    out = Path("artifacts/gismeteo_moscow.png"); out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True); page = browser.new_page(viewport={"width": 900, "height": 720}, device_scale_factor=1.5)
        page.goto(GISMETEO_MOSCOW_DAY, wait_until="domcontentloaded", timeout=45000); page.wait_for_timeout(5000); page.screenshot(path=str(out), full_page=False); browser.close()
    return out


def send_gismeteo(token: str, chat_id: str) -> None:
    caption = "🌦 GISMETEO · МОСКВА · ПРОГНОЗ НА ДЕНЬ\n" + GISMETEO_MOSCOW_DAY
    try: telegram_send_photo(token, chat_id, make_gismeteo_card(), caption)
    except Exception as exc:
        print(f"WARN gismeteo-card fallback recipient={chat_id}: {exc}"); telegram_send(token, chat_id, caption, preview=True)


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN"); raw_ids = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not raw_ids: raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    text = weather_block() + "\n\n" + finance_block(); failures = 0
    for chat_id in parse_chat_ids(raw_ids):
        try:
            telegram_send(token, chat_id, text); send_gismeteo(token, chat_id); print(f"PASS personal-morning recipient={chat_id}")
        except Exception as exc:
            failures += 1; print(f"FAIL personal-morning recipient={chat_id}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
