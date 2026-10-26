"""Help: the guides (app/api/data/docs/help/*.md), listed in order and read one by one."""


def seed(s):
    pass


def test_guides_listed_in_order(client):
    guides = client.get("/api/help").json()
    assert [g["slug"] for g in guides][:2] == ["first-steps", "cellar"]
    assert all(g["title"] and g["summary"] for g in guides)


def test_a_guide(client):
    g = client.get("/api/help/cellar").json()
    assert g["title"] == "Your cellar and its shelf map" and g["summary"].startswith("What you hold")
    assert g["body"].startswith("## Adding bottles") and not g["body"].startswith(g["summary"])
    assert g["prev"]["slug"] == "first-steps" and g["next"]["slug"] == "tastings"
    assert client.get("/api/help/first-steps").json()["prev"] is None
    assert client.get("/api/help/nothing").status_code == 404
