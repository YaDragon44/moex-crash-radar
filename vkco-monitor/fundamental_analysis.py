from __future__ import annotations
from typing import Any
import requests
URL="https://vk.company.ru/ru/investors/info/12383/"
FACTS={"revenue_h1_bln":81.0,"revenue_yoy_pct":12.0,"ebitda_h1_bln":14.0,"ebitda_yoy_pct":34.0,"ebitda_margin_pct":17.0,"operating_cash_flow_bln":15.4,"net_debt_bln":60.2,"net_debt_change_pct":-27.0,"net_debt_ebitda":2.3,"cash_bln":49.6,"q2_net_profit_bln":0.328,"vk_tech_revenue_yoy_pct":35.0,"vk_dau_mln":90.7,"guidance_ebitda_2026_bln":24.0}
def _light(value,green,yellow,higher=True):
    return ("GREEN" if value>=green else "YELLOW" if value>=yellow else "RED") if higher else ("GREEN" if value<=green else "YELLOW" if value<=yellow else "RED")
def fetch_analysis()->dict[str,Any]:
    try:
        r=requests.get(URL,timeout=20);r.raise_for_status()
        if "2026" not in r.text: raise ValueError("unexpected release")
    except Exception as exc:
        return {"status":"DATA_UNAVAILABLE","error":type(exc).__name__,"source_url":URL}
    f=FACTS.copy()
    indicators=[
      {"label":"Выручка · рост г/г","value":f["revenue_yoy_pct"],"unit":"%","light":_light(f["revenue_yoy_pct"],10,5)},
      {"label":"EBITDA · рост г/г","value":f["ebitda_yoy_pct"],"unit":"%","light":_light(f["ebitda_yoy_pct"],20,5)},
      {"label":"EBITDA margin","value":f["ebitda_margin_pct"],"unit":"%","light":_light(f["ebitda_margin_pct"],15,10)},
      {"label":"Чистый долг / EBITDA","value":f["net_debt_ebitda"],"unit":"x","light":_light(f["net_debt_ebitda"],2.5,3.5,False)},
      {"label":"Операционный денежный поток","value":f["operating_cash_flow_bln"],"unit":"млрд ₽","light":"GREEN" if f["operating_cash_flow_bln"]>0 else "RED"},
      {"label":"Чистый долг · изменение","value":f["net_debt_change_pct"],"unit":"%","light":"GREEN" if f["net_debt_change_pct"]<0 else "RED"}]
    return {"status":"OK","as_of":"2026-06-30","published_at":"2026-08-13","source":"VK IR · H1 2026","source_url":URL,"facts":f,"indicators":indicators,"positives":["Выручка H1 2026 +12% г/г; EBITDA +34%, маржа 17%.","Операционный денежный поток 15,4 млрд ₽.","Чистый долг -27%; Net debt/EBITDA 2,3x.","VK Tech: выручка +35% г/г."],"risks":["Чистый долг остаётся существенным: 60,2 млрд ₽.","Дальнейшее улучшение требует сохранения дисциплины затрат и денежного потока.","H1 2026 — неаудированная отчётность."],"conclusion":"Фундаментальный импульс улучшается: прибыльность, денежный поток и долговая нагрузка движутся в благоприятную сторону при сохранении долгового риска.","recommendation":"WATCH POSITIVE: фундаментальный контекст положительный, но не является самостоятельным торговым сигналом. Контролировать Net debt/EBITDA, денежный поток, маржу и guidance EBITDA >24 млрд ₽.","read_only":True}
