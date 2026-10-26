"""About the data: the sources and how it was built (the Markdown files the README links to), and what the database
holds."""
from db import Appellation, Region, Varietal, Vineyard


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    napa = Region(name="California", country="United States")
    s.add_all([
        Appellation(name="Volnay", region_obj=burgundy, type="AOP", boundary="inao:1"),
        Appellation(name="Pommard", region_obj=burgundy, type="AOP"),
        Appellation(name="Napa Valley", region_obj=napa, type="AVA", boundary="ava:napa"),
        Vineyard(name="Clos des Ducs", region_obj=burgundy, boundary="vineyard:bourgogne:1"),
        Varietal(name="Pinot Noir", color="Red", vivc=9279, parents="Savagnin", climate="Cool"),
        Varietal(name="Savagnin", color="White"),
        Varietal(name="Gamay"),
    ])


def test_about_the_data(client):
    d = client.get("/api/about/data").json()
    assert "## Reference data" in d["sources"] and "INAO" in d["sources"] and "## How it was built" in d["built"]
    assert d["counts"] == {"regions": 2, "countries": 2, "appellations": 3, "appellations_outlined": 2,
                           "vineyards": 1, "vineyards_outlined": 1, "grapes": 3,
                           "grapes_vivc": 1, "grapes_parents": 1, "grapes_profile": 1}
    assert d["by_country"] == [{"name": "France", "count": 2}, {"name": "United States", "count": 1}]
    assert d["by_type"] == [{"name": "AOP", "count": 2}, {"name": "AVA", "count": 1}]
    assert isinstance(d["map_credits"], list)
