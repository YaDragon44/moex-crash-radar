from yandex_consensus import parse_consensus

def test_parse_yandex_consensus_aggregate():
    html = """<html><body>
    <h2>Прогноз цены</h2><div>Обновлено 24 сентября 2026</div>
    <div>255,03 ₽ +124,99%</div><div>От 160 ₽</div><div>Макс 345 ₽</div>
    <div>Мнения аналитиков: Держать</div>
    <div>0 Продавать 4 Держать 4 Покупать</div>\n    <div>Газпромбанк Инвестиции Прогноз до 22 сентября 2027 Держать 160 ₽ +41,41%</div>\n    <div>БКС Мир инвестиций Прогноз до 21 сентября 2027 Покупать 200 ₽ +76,76%</div>\n    <div>Freedom Finance Global Прогноз до 21 сентября 2027 Держать 345 ₽ +204,90%</div>
    </body></html>"""
    x=parse_consensus(html, observed_at="2026-09-24T14:00:00+03:00")
    assert x["status"]=="OK"
    assert x["consensus_target"]==255.03
    assert x["target_low"]==160
    assert x["target_high"]==345
    assert (x["sell"],x["hold"],x["buy"],x["analyst_count"])==(0,4,4,8)\n    assert len(x["analysts"])==3\n    assert x["analysts"][0]["name"]=="Газпромбанк Инвестиции"\n    assert x["analysts"][1]["target"]==200\n    assert x["analysts"][2]["upside_pct"]==204.90

def test_fail_closed_when_consensus_absent():
    try:
        parse_consensus("<html><body>VKCO</body></html>")
    except ValueError as exc:
        assert str(exc)=="YANDEX_CONSENSUS_NOT_FOUND"
    else:
        raise AssertionError("must fail closed")
