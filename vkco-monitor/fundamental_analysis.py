from __future__ import annotations
from typing import Any
import re
import requests

URL="https://vk.company.ru/ru/investors/info/12383/"

def _num(s:str)->float:
    return float(s.replace("\u00a0"," ").replace(" ","").replace(",", "."))

def parse_release(text:str)->dict[str,float]:
    clean=re.sub(r"<[^>]+>"," ",text)
    clean=re.sub(r"\s+"," ",clean).replace("₽","руб.")
    patterns={
      "revenue_h1_bln":r"первого полугодия 2026 года увеличилась на\s*([\d,.]+)%[^.]*?до\s*([\d,.]+)\s*млрд руб",
      "ebitda_h1_bln":r"EBITDA VK за первое полугодие 2026 года вырос(?:ла)? на\s*([\d,.]+)%[^.]*?до\s*([\d,.]+)\s*млрд",
      "ebitda_margin_pct":r"Рентабельность по EBITDA достигла\s*([\d,.]+)%",
      "operating_cash_flow_bln":r"операционный денежный поток вырос до\s*([\d,.]+)\s*млрд",
      "net_debt_bln":r"Чистый долг[^.]*?уменьшился на\s*([\d,.]+)%\s*до\s*([\d,.]+)\s*млрд",
      "cash_bln":r"свободных денежных средств вырос[^.]*?до\s*([\d,.]+)\s*млрд",
      "net_debt_ebitda":r"Чистый долг/EBITDA[^.]*?составило\s*([\d,.]+)х",
      "q2_net_profit_bln":r"Чистая прибыль[^.]*?составила\s*([\d,.]+)\s*млн руб",
      "vk_tech_revenue_yoy_pct":r"Выручка VK Tech увеличилась на\s*([\d,.]+)%\s*до",
      "vk_dau_mln":r"Средняя дневная аудитория сервисов VK[^.]*?до\s*([\d,.]+)\s*млн",
      "guidance_ebitda_2026_bln":r"прогноз по EBITDA на 2026 год[^.]*?более\s*([\d,.]+)\s*млрд",
    }
    vals={}
    for key,p in patterns.items():
        m=re.search(p,clean,re.I)
        if not m: raise ValueError(f"missing:{key}")
        g=[_num(x) for x in m.groups()]
        if key=="revenue_h1_bln": vals["revenue_yoy_pct"],vals[key]=g
        elif key=="ebitda_h1_bln": vals["ebitda_yoy_pct"],vals[key]=g
        elif key=="net_debt_bln": vals["net_debt_change_pct"],vals[key]=-g[0],g[1]
        elif key=="q2_net_profit_bln": vals[key]=g[0]/1000.0
        else: vals[key]=g[-1]
    return vals

def _light(value,green,yellow,higher=True):
    return ("GREEN" if value>=green else "YELLOW" if value>=yellow else "RED") if higher else ("GREEN" if value<=green else "YELLOW" if value<=yellow else "RED")

def fetch_analysis()->dict[str,Any]:
    try:
        r=requests.get(URL,timeout=20);r.raise_for_status();f=parse_release(r.text)
    except Exception as exc:
        return {"status":"DATA_UNAVAILABLE","error":type(exc).__name__,"source_url":URL}
    indicators=[
      {"label":"Выручка · рост г/г","value":f["revenue_yoy_pct"],"unit":"%","light":_light(f["revenue_yoy_pct"],10,5)},
      {"label":"EBITDA · рост г/г","value":f["ebitda_yoy_pct"],"unit":"%","light":_light(f["ebitda_yoy_pct"],20,5)},
      {"label":"EBITDA margin","value":f["ebitda_margin_pct"],"unit":"%","light":_light(f["ebitda_margin_pct"],15,10)},
      {"label":"Чистый долг / EBITDA","value":f["net_debt_ebitda"],"unit":"x","light":_light(f["net_debt_ebitda"],2.5,3.5,False)},
      {"label":"Операционный денежный поток","value":f["operating_cash_flow_bln"],"unit":"млрд ₽","light":"GREEN" if f["operating_cash_flow_bln"]>0 else "RED"},
      {"label":"Чистый долг · изменение","value":f["net_debt_change_pct"],"unit":"%","light":"GREEN" if f["net_debt_change_pct"]<0 else "RED"}]
    return {"status":"OK","as_of":"2026-06-30","published_at":"2026-08-13","source":"VK IR · H1 2026","source_url":URL,"facts":f,"indicators":indicators,
    "positives":[f'Выручка H1 2026 +{f["revenue_yoy_pct"]:g}% г/г; EBITDA +{f["ebitda_yoy_pct"]:g}%, маржа {f["ebitda_margin_pct"]:g}%.',f'Операционный денежный поток {f["operating_cash_flow_bln"]:g} млрд ₽.',f'Чистый долг {f["net_debt_change_pct"]:g}%; Net debt/EBITDA {f["net_debt_ebitda"]:g}x.',f'VK Tech: выручка +{f["vk_tech_revenue_yoy_pct"]:g}% г/г.'],
    "risks":[f'Чистый долг остаётся существенным: {f["net_debt_bln"]:g} млрд ₽.','Дальнейшее улучшение требует сохранения дисциплины затрат и денежного потока.','H1 2026 — неаудированная отчётность.'],
    "conclusion":"Фундаментальный импульс улучшается: прибыльность, денежный поток и долговая нагрузка движутся в благоприятную сторону при сохранении долгового риска.",
    "recommendation":f'WATCH POSITIVE: фундаментальный контекст положительный, но не является самостоятельным торговым сигналом. Контролировать Net debt/EBITDA, денежный поток, маржу и guidance EBITDA >{f["guidance_ebitda_2026_bln"]:g} млрд ₽.',"read_only":True}
