"""Grape descriptions from Wikipedia. The network is never used: wiki._get_json is replaced."""
import urllib.error

import pytest

import wiki
from db import Region, Varietal


def seed(s):
    s.add_all([Region(name="Bourgogne"), Varietal(name="Chenin Blanc"), Varietal(name="Savagnin"),
               Varietal(name="Trousseau"), Varietal(name="Mondeuse")])


def summary(title, extract, thumb=None):
    return {"type": "standard", "title": title, "description": "Grape variety", "extract": extract,
            "thumbnail": {"source": f"https://upload.wikimedia.org/thumb/x/320px-{title}.jpg"} if thumb is not False else None,
            "originalimage": {"source": f"https://upload.wikimedia.org/x/{title}.jpg"},
            "content_urls": {"desktop": {"page": f"https://en.wikipedia.org/wiki/{title}"}}}


@pytest.fixture
def web(monkeypatch):
    pages, calls = {}, []

    def fake(url):
        calls.append(url)
        for key, value in pages.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        return None  # 404
    monkeypatch.setattr(wiki, "_get_json", fake)
    return pages, calls


def test_grape_tries_the_grape_article_first_and_is_cached(client, web):
    pages, calls = web
    pages["summary/Chenin_Blanc_%28grape%29"] = None
    pages["summary/Chenin_Blanc"] = summary("Chenin blanc", "Chenin blanc is a white wine grape variety from the Loire.")
    g = client.get("/api/grapes/chenin blanc/about").json()
    assert g["found"] and g["title"] == "Chenin blanc" and "grape" in g["extract"]
    assert g["image"].endswith("/320px-Chenin blanc.jpg")  # Wikipedia's own thumbnail size: others may not exist
    n = len(calls)
    assert client.get("/api/grapes/Chenin Blanc/about").json() == g
    assert len(calls) == n  # second view: from the cache


def test_pages_not_about_wine_are_skipped(client, web):
    pages, _ = web
    # Most specific first: the fake matches URLs (titles URL-encoded) by substring, in this order
    pages["summary/Trousseau_%28grape%29"] = None
    pages["summary/Trousseau_%28wine_grape%29"] = summary("Trousseau (wine grape)", "Trousseau is a red wine grape from the Jura.")
    pages["summary/Trousseau"] = summary("Trousseau", "A trousseau is the clothing a bride gathers before marriage.")  # not wine
    pages["list=search"] = {"query": {"search": [{"title": "Trousseau (wine grape)"}]}}
    assert client.get("/api/grapes/Trousseau/about").json()["title"] == "Trousseau (wine grape)"


def test_search_hits_about_another_grape_are_skipped(client, web):
    pages, _ = web
    # Nothing under the expected titles; search only finds another grape's article
    pages["list=search"] = {"query": {"search": [{"title": "Syrah"}]}}
    pages["summary/Syrah"] = summary("Syrah", "Syrah is a red wine grape.")
    assert client.get("/api/grapes/Mondeuse/about").json()["found"] is False


def test_offline_is_not_cached(client, web):
    pages, _ = web
    pages["summary/"] = urllib.error.URLError("no network")
    assert client.get("/api/grapes/Savagnin/about").json() == {"found": False, "error": "Wikipedia couldn't be reached"}
    del pages["summary/"]
    pages["summary/Savagnin"] = summary("Savagnin", "Savagnin is a white wine grape.")
    assert client.get("/api/grapes/Savagnin/about").json()["title"] == "Savagnin"  # tried again, not cached


def test_regions_have_no_wikipedia_card(client, web):
    _, calls = web
    assert client.get("/api/regions/Bourgogne/about").status_code == 404
    assert not calls  # Wikipedia isn't asked
