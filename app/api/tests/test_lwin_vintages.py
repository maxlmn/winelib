"""An LWIN across the vintages of a cuvée: the wine form shares it, and spread_lwin (the LWIN codes task's run) gives
it to the vintages without one; vintages that disagree are left alone."""
from db import Appellation, Producer, Region, Wine


def seed(s):
    loire = Region(name="Loire", country="France")
    sc = Appellation(name="Saumur-Champigny", region_obj=loire)
    p = Producer(name="Clos Rougeard")
    s.add_all([
        Wine(producer=p, cuvee="Le Bourg", vintage="2019", type="Red", appellation=sc, lwin="1234567"),
        Wine(producer=p, cuvee="Le Bourg", vintage="2018", type="Red", appellation=sc),  # 2: gets it
        Wine(producer=p, cuvee="Le Bourg", vintage="2017", type="Red", appellation=sc, lwin="12345672017"),  # LWIN11
        Wine(producer=p, cuvee="Le Bourg", vintage="2016", type="White", appellation=sc),  # 4: another colour
        Wine(producer=p, cuvee="Les Poyeux", vintage="2019", type="Red", appellation=sc, lwin="1111111"),
        Wine(producer=p, cuvee="Les Poyeux", vintage="2018", type="Red", appellation=sc, lwin="2222222"),  # disagree
        Wine(producer=p, cuvee="Les Poyeux", vintage="2017", type="Red", appellation=sc),  # 7: left alone
        Wine(producer=p, cuvee="Le Clos", vintage="2019", type="Red", appellation=sc),  # 8
        Wine(producer=p, cuvee="Le Clos", vintage="2018", type="Red", appellation=sc),  # 9
    ])


def lwin(client, wine_id):
    return client.get(f"/api/wines/{wine_id}").json()["lwin"]


def test_spread_to_other_vintages(client):
    from tasks.match_lwin import spread_lwin
    from db import get_session
    from main import app
    s = next(app.dependency_overrides[get_session]())
    filled, conflicts = spread_lwin(s, commit=True, log=lambda line: None)
    assert [(w.id, code) for w, code in filled] == [(2, "1234567")]
    assert [sorted(codes) for _, codes in conflicts] == [["1111111", "2222222"]]  # Les Poyeux: left alone
    s.close()
    assert [lwin(client, i) for i in (2, 4, 7)] == ["1234567", None, None]


def test_form_shares_it(client):
    form = {"producer": 1, "cuvee": "Le Clos", "vintage": "2019", "type": "Red", "appellation": 1, "lwin": "7654321"}
    assert client.put("/api/wines/8", json=form).status_code == 200
    assert lwin(client, 9) == "7654321"  # given to the other vintage
    r = client.post("/api/wines", json={**form, "vintage": "2020", "lwin": ""})
    assert lwin(client, r.json()["id"]) == "7654321"  # a new vintage takes it
