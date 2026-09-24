import latest_news as n

def test_parse():
    raw="<div>24 сентября 2026 VK опубликовала результаты за период</div><div>20 сентября 2026 Совет директоров рассмотрел вопрос</div>"
    x=n.parse_latest(raw)
    assert len(x)==2
    assert x[0]["date"]=="24 сентября 2026"
    assert "результаты" in x[0]["text"]

def test_fail_closed(monkeypatch):
    def boom(*a,**k): raise RuntimeError("x")
    monkeypatch.setattr(n.requests,"get",boom)
    assert n.fetch_latest()["status"]=="DATA_UNAVAILABLE"
