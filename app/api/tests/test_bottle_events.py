"""What happened to a bottle besides being drunk: gifted, sold, broken. Recording it takes it off the count, undoing
it puts it back; the bottle page tells its story (these and the tastings)."""
from datetime import date

from db import Bottle, Producer, TastingNote, Wine


def seed(s):
    p = Producer(name="Domaine Huet")
    w = Wine(producer=p, cuvee="Le Mont Sec", vintage="2019", type="White")
    s.add_all([p, w])
    s.flush()
    b = Bottle(wine_id=w.id, qty=6, location="H1", price=40, currency="EUR")
    s.add(b)
    s.flush()
    s.add(TastingNote(bottle_id=b.id, date=date(2026, 9, 1), rating=93))


def bottle(client):
    wid = next(r["id"] for r in client.get("/api/search", params={"q": "mont sec"}).json()["results"] if r["kind"] == "wine")
    return client.get(f"/api/wines/{wid}").json()["cellar"][0]["bottle_id"]


def test_gifted_sold_broken_and_undone(client):
    bid = bottle(client)
    out = lambda **b: client.post(f"/api/bottles/{bid}/out", json=b)  # noqa: E731
    assert out(kind="gifted", qty=2, date="2026-10-01", note="to Claude").json()["qty"] == 4
    sold = out(kind="sold", price=55).json()
    assert sold["qty"] == 3
    assert out(kind="broken", note="dropped").json()["qty"] == 2
    # not more than there is, not a kind that isn't one
    assert out(kind="gifted", qty=3).status_code == 409
    assert out(kind="drunk").status_code == 422

    d = client.get(f"/api/bottles/{bid}").json()
    assert d["qty"] == 2
    kinds = {e["kind"]: e for e in d["events"]}
    assert kinds["gifted"]["qty"] == 2 and kinds["gifted"]["note"] == "to Claude"
    assert (kinds["sold"]["price"], kinds["sold"]["currency"]) == (55, "EUR")  # the bottle's currency
    assert kinds["broken"]["price"] is None
    assert [t["date"] for t in d["drunk"]] == ["2026-09-01"]

    # undone: back in the cellar
    assert client.delete(f"/api/bottles/{bid}/out/{sold['id']}").json()["qty"] == 3
    assert len(client.get(f"/api/bottles/{bid}").json()["events"]) == 2
