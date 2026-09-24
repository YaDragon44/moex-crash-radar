import fundamental_snapshot as f

class R:
    def raise_for_status(self): pass
    def json(self):
        return {"securities":{"columns":["SECID","SHORTNAME","LOTSIZE","ISSUESIZE","ISIN","LISTLEVEL"],"data":[["VKCO","МКПАО ВК",1,572904180,"RU000A106YF0",1]]}}

def test_snapshot(monkeypatch):
    monkeypatch.setattr(f.requests,"get",lambda *a,**k:R())
    x=f.fetch_snapshot(114.1)
    assert x["status"]=="OK"
    assert x["issue_size"]==572904180
    assert x["market_cap_rub"]==round(114.1*572904180,2)
    assert x["isin"]=="RU000A106YF0"

def test_fail_closed(monkeypatch):
    def boom(*a,**k): raise RuntimeError("x")
    monkeypatch.setattr(f.requests,"get",boom)
    assert f.fetch_snapshot(114.1)["status"]=="DATA_UNAVAILABLE"
