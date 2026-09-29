import fundamental_analysis as f
SAMPLE="""<html>Выручка VK по итогам первого полугодия 2026 года увеличилась на 12% год к году до 81 млрд руб.
Показатель EBITDA VK за первое полугодие 2026 года вырос на 34% год к году до 14 млрд руб.
Рентабельность по EBITDA достигла 17%. Чистый операционный денежный поток вырос до 15,4 млрд руб.
Чистый долг на конец первого полугодия уменьшился на 27% до 60,2 млрд руб. Объем свободных денежных средств вырос на 51% до 49,6 млрд руб.
Соотношение Чистый долг/EBITDA улучшилось и составило 2,3х. Чистая прибыль по итогам второго квартала 2026 года составила 328 млн руб.
Выручка VK Tech увеличилась на 35% до 9 млрд руб. Средняя дневная аудитория сервисов VK увеличилась на 13,2 млн до 90,7 млн пользователей.
Компания сохраняет прогноз по EBITDA на 2026 год в размере более 24 млрд руб.</html>"""
class R:
    text=SAMPLE
    def raise_for_status(self): pass

def test_parser_extracts_official_release_facts():
    x=f.parse_release(SAMPLE)
    assert x["revenue_h1_bln"]==81.0 and x["revenue_yoy_pct"]==12.0
    assert x["ebitda_h1_bln"]==14.0 and x["ebitda_yoy_pct"]==34.0
    assert x["net_debt_bln"]==60.2 and x["net_debt_change_pct"]==-27.0
    assert x["q2_net_profit_bln"]==0.328 and x["guidance_ebitda_2026_bln"]==24.0

def test_contract(monkeypatch):
    monkeypatch.setattr(f.requests,"get",lambda *a,**k:R())
    x=f.fetch_analysis();assert x["status"]=="OK";assert x["read_only"] is True;assert len(x["indicators"])==6
    assert {i["light"] for i in x["indicators"]}<={"GREEN","YELLOW","RED"}

def test_source_failure_fails_closed(monkeypatch):
    def boom(*a,**k): raise f.requests.RequestException("offline")
    monkeypatch.setattr(f.requests,"get",boom)
    x=f.fetch_analysis();assert x["status"]=="DATA_UNAVAILABLE";assert x["source_url"]==f.URL
    assert "facts" not in x and "indicators" not in x

def test_unexpected_release_fails_closed(monkeypatch):
    class BadR:
        text="unexpected content"
        def raise_for_status(self): pass
    monkeypatch.setattr(f.requests,"get",lambda *a,**k:BadR())
    x=f.fetch_analysis();assert x["status"]=="DATA_UNAVAILABLE";assert x["error"]=="ValueError"
