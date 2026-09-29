import fundamental_analysis as f
class R:
    text="2026"
    def raise_for_status(self): pass
def test_contract(monkeypatch):
    monkeypatch.setattr(f.requests,"get",lambda *a,**k:R())
    x=f.fetch_analysis();assert x["status"]=="OK";assert x["read_only"] is True;assert len(x["indicators"])==6
    assert {i["light"] for i in x["indicators"]}<={"GREEN","YELLOW","RED"}


def test_source_failure_fails_closed(monkeypatch):
    def boom(*a,**k): raise f.requests.RequestException("offline")
    monkeypatch.setattr(f.requests,"get",boom)
    x=f.fetch_analysis()
    assert x["status"]=="DATA_UNAVAILABLE"
    assert x["source_url"]==f.URL
    assert "facts" not in x
    assert "indicators" not in x

def test_unexpected_release_fails_closed(monkeypatch):
    class BadR:
        text="unexpected content"
        def raise_for_status(self): pass
    monkeypatch.setattr(f.requests,"get",lambda *a,**k:BadR())
    x=f.fetch_analysis()
    assert x["status"]=="DATA_UNAVAILABLE"
    assert x["error"]=="ValueError"
