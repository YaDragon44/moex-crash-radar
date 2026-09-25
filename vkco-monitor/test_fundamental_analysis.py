import fundamental_analysis as f
class R:
    text="2026"
    def raise_for_status(self): pass
def test_contract(monkeypatch):
    monkeypatch.setattr(f.requests,"get",lambda *a,**k:R())
    x=f.fetch_analysis();assert x["status"]=="OK";assert x["read_only"] is True;assert len(x["indicators"])==6
    assert {i["light"] for i in x["indicators"]}<={"GREEN","YELLOW","RED"}
