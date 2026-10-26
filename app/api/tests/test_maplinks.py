"""Google Maps links → coordinates. The network is never used: maplinks._open is replaced."""
import pytest

import maplinks


def seed(session):
    pass


ODETTE_FULL = ("https://www.google.com/maps/place/Odette/@1.2899,103.8505,17z/data=!3m1!4b1!4m6!3m5"
               "!1s0x31da19a0b5e9e5b5:0x2f0e!8m2!3d1.2902655!4d103.8515131!16s%2Fg%2F11b6?entry=tts")


@pytest.fixture
def web(monkeypatch):
    """Maps a URL to (final URL, page) and records what was opened."""
    pages, opened = {}, []

    def fake_open(url):
        opened.append(url)
        if url not in pages:
            raise maplinks.LinkError("unexpected fetch")
        return pages[url]
    monkeypatch.setattr(maplinks, "_open", fake_open)
    monkeypatch.setattr(maplinks, "_geocode", lambda q: None)
    return pages, opened


def test_full_link_uses_the_pin_not_the_viewport(web):
    r = maplinks.resolve(ODETTE_FULL)
    assert (r["lat"], r["lng"], r["name"]) == (1.2902655, 103.8515131, "Odette")
    assert web[1] == []  # nothing to fetch


def test_short_link_is_followed(web):
    short = "https://maps.app.goo.gl/fW1PWSXhTQ2NMCM26?g_st=ic"
    web[0][short] = (ODETTE_FULL, "")
    assert maplinks.resolve(short) == {"lat": 1.2902655, "lng": 103.8515131, "name": "Odette"}


def test_share_link_without_coordinates_reads_the_page(web):
    short = "https://maps.app.goo.gl/abc"
    final = "https://www.google.com/maps?q=Odette,+1+St+Andrew%27s+Rd,+Singapore&ftid=0x31da19a0:0x2f0e&g_st=ic"
    page = '<meta content="https://maps.google.com/maps/api/staticmap?center=1.29%2C103.85&amp;zoom=15&amp;markers=1.2902655%2C103.8515131&amp;size=256x256" property="og:image">'
    web[0][short] = (final, page)
    assert maplinks.resolve(short) == {"lat": 1.2902655, "lng": 103.8515131, "name": "Odette"}


def test_the_page_map_centre_is_never_used(web, monkeypatch):
    """Google centres a bare map on the requester (the server): that "current location" must not be taken."""
    short = "https://maps.app.goo.gl/here"
    final = "https://www.google.com/maps?q=Odette,+1+St+Andrew%27s+Rd,+Singapore+178957&ftid=0x31da19a0:0x2f0e"
    page = '<meta content="https://maps.google.com/maps/api/staticmap?center=1.3521%2C103.8198&amp;zoom=11" property="og:image">' \
           ' window.APP_INITIALIZATION_STATE=[[[40000,103.8198,1.3521]]] href="/maps/@1.3521,103.8198,11z"'
    web[0][short] = (final, page)
    looked_up = []
    monkeypatch.setattr(maplinks, "_geocode", lambda q: looked_up.append(q) or (1.29027, 103.85152))
    r = maplinks.resolve(short)
    assert (r["lat"], r["lng"], r["name"], r["approximate"]) == (1.29027, 103.85152, "Odette", True)
    assert looked_up == ["Odette, 1 St Andrew's Rd, Singapore 178957"]  # the full address goes to the geocoder


def test_a_bare_map_viewport_is_not_a_place(web):
    short = "https://maps.app.goo.gl/bare"
    web[0][short] = ("https://www.google.com/maps/@1.3521,103.8198,11z", "")
    with pytest.raises(maplinks.LinkError, match="paste the coordinates"):
        maplinks.resolve(short)


def test_place_url_viewport_still_counts():
    assert maplinks.url_coordinates("https://www.google.com/maps/place/Odette/@1.2899,103.8505,17z") == (1.2899, 103.8505)


def test_consent_page_keeps_the_real_url(web):
    short = "https://maps.app.goo.gl/eu"
    web[0][short] = ("https://consent.google.com/m?continue=" + ODETTE_FULL.replace("/", "%2F").replace("?", "%3F"), "")
    assert maplinks.resolve(short)["lat"] == 1.2902655


def test_query_and_search_forms():
    assert maplinks.find_coordinates("https://maps.google.com/?q=48.8566,2.3522") == (48.8566, 2.3522)
    assert maplinks.find_coordinates("https://www.google.com/maps/search/-33.86,+151.21") == (-33.86, 151.21)


def test_only_google_links(web):
    for bad in ("https://evil.example/maps", "file:///etc/passwd", "http://169.254.169.254/", "https://google.com.evil.io/x"):
        with pytest.raises(maplinks.LinkError):
            maplinks.resolve(bad)
    assert web[1] == []
    assert maplinks.is_google("https://www.google.com.sg/maps/@1,2,3z")


def test_redirect_outside_google_is_refused():
    handler = maplinks._GoogleOnly()
    with pytest.raises(maplinks.LinkError):
        handler.redirect_request(None, None, 302, "Found", {}, "http://169.254.169.254/latest")


def test_endpoint(client, web):
    web[0]["https://maps.app.goo.gl/x"] = (ODETTE_FULL, "")
    assert client.get("/api/lookups/map-link", params={"url": "https://maps.app.goo.gl/x"}).json()["name"] == "Odette"
    bad = client.get("/api/lookups/map-link", params={"url": "https://example.com"})
    assert bad.status_code == 422 and bad.json()["detail"] == "Not a Google Maps link"
