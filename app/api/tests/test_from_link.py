"""Fill a wine from a link: a page's product details, and its name read into producer, cuvée, vintage, appellation,
colour and size against the database (the page fetched in a test: no network)."""
from db import Appellation, Producer, Region, Varietal, Wine


def seed(s):
    loire = Region(name="Loire", country="France")
    bourgogne = Region(name="Bourgogne", country="France")
    s.add_all([loire, bourgogne,
               Producer(name="Clos Rougeard", region_obj=loire), Producer(name="Domaine Jean-Marc Vincent", region_obj=bourgogne),
               Appellation(name="Saumur-Champigny", region_obj=loire), Appellation(name="Santenay Premier Cru", region_obj=bourgogne)])
    s.flush()
    rougeard = s.query(Producer).filter_by(name="Clos Rougeard").one()
    sc = s.query(Appellation).filter_by(name="Saumur-Champigny").one()
    w = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2015", type="Red", appellation=sc, region_obj=loire, lwin="1012345")
    w.set_grapes([(Varietal(name="Cabernet Franc"), None)])
    s.add(w)


LD_PAGE = """<html><head><title>Clos Rougeard Le Bourg 2016 Saumur-Champigny | Some Shop</title>
<meta property="og:image" content="https://shop.example/og.jpg">
<script type="application/ld+json">{"@context": "https://schema.org", "@graph": [{"@type": "BreadcrumbList"},
 {"@type": "Product", "name": "Clos Rougeard Le Bourg 2016, Saumur-Champigny Rouge", "brand": {"@type": "Brand", "name": "Clos Rougeard"},
  "image": ["https://shop.example/bourg.jpg"], "offers": {"@type": "Offer", "price": "395.00", "priceCurrency": "EUR"}}]}</script>
</head><body></body></html>"""

OG_PAGE = """<html><head><title>x</title>
<meta property="og:title" content="Domaine Jean-Marc Vincent Santenay 1er Cru Le Beaurepaire Blanc 2022 Magnum | Vivino">
<meta property="og:image" content="https://images.example/beaurepaire.png">
</head></html>"""


def fill(client, monkeypatch, page):
    from tasks import from_link
    monkeypatch.setattr(from_link, "fetch", lambda url: page)
    r = client.get("/api/lookups/from-link", params={"url": "https://shop.example/wine"})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_shop_page_with_product_data(client, monkeypatch):
    w = fill(client, monkeypatch, LD_PAGE)
    assert w["producer"]["name"] == "Clos Rougeard" and w["producer"]["id"]
    assert (w["cuvee"], w["vintage"], w["type"]) == ("Le Bourg", "2016", "Red")
    assert w["appellation"]["name"] == "Saumur-Champigny" and w["region"]["name"] == "Loire"
    assert (w["image"], w["price"], w["currency"]) == ("https://shop.example/bourg.jpg", 395.0, "EUR")


def test_a_page_with_only_its_title(client, monkeypatch):
    w = fill(client, monkeypatch, OG_PAGE)
    assert w["producer"]["name"] == "Domaine Jean-Marc Vincent"
    assert (w["cuvee"], w["vintage"], w["type"], w["size"]) == ("Le Beaurepaire", "2022", "White", "150cl")
    assert w["appellation"]["name"] == "Santenay Premier Cru"  # "1er Cru" read as "Premier Cru"
    assert w["image"] == "https://images.example/beaurepaire.png"


def test_an_unknown_producer_is_a_name_to_create(client, monkeypatch):
    page = LD_PAGE.replace("Clos Rougeard", "Domaine des Miroirs").replace("Le Bourg", "Entre Deux Bleus")
    w = fill(client, monkeypatch, page)
    assert w["producer"] == {"id": None, "name": "Domaine des Miroirs"}
    assert w["cuvee"] == "Entre Deux Bleus"


def test_not_a_web_address(client):
    r = client.get("/api/lookups/from-link", params={"url": "file:///etc/passwd"})
    assert r.status_code == 422 and "web address" in r.json()["detail"]


def test_a_cuvee_you_have_fills_the_rest(client, monkeypatch):
    """A shop's short name ("Bourg", no colour) read as your cuvée: its spelling, colour, appellation, grapes, LWIN."""
    page = """<html><head><meta property="og:title" content="2016 Clos Rougeard, Saumur-Champigny, Bourg"></head></html>"""
    w = fill(client, monkeypatch, page)
    assert (w["cuvee"], w["vintage"], w["type"]) == ("Le Bourg", "2016", "Red")
    assert w["appellation"]["name"] == "Saumur-Champigny" and w["lwin"] == "1012345"
    assert [g["name"] for g in w["grapes"]] == ["Cabernet Franc"] and w["wine_id"] is None
    # the same vintage as yours: that wine
    w = fill(client, monkeypatch, page.replace("2016", "2015"))
    assert w["wine_id"]


def test_local_addresses_refused(monkeypatch):
    """A link to this machine or the local network (the NAS's admin page) is never fetched, nor a redirect to one."""
    import socket
    import pytest
    from tasks import from_link
    answers = {"nas.local": "192.168.1.2", "shop.example": "93.184.216.34", "meta": "169.254.169.254", "me": "127.0.0.1"}
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(0, 0, 0, "", (answers[host], 0))])
    assert from_link.public("https://shop.example/wine")
    for url in ("http://nas.local:5000/", "http://meta/latest", "http://me:8000/api/settings", "http://[::1]/"):
        if "[::1]" in url:
            monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(0, 0, 0, "", ("::1", 0, 0, 0))])
        assert not from_link.public(url), url
        with pytest.raises(from_link.LinkError):
            from_link.fetch(url)
    # a public page redirecting to the local network: refused at the redirect
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(0, 0, 0, "", (answers.get(host, "93.184.216.34"), 0))])
    with pytest.raises(from_link.LinkError):
        from_link._PublicOnly().redirect_request(None, None, 302, "Found", {}, "http://nas.local/admin")


def _answers(monkeypatch, *answers):
    """socket.getaddrinfo answering each lookup with the next list of addresses (the last one repeated)"""
    import socket
    calls = []

    def getaddrinfo(host, port=None, *a, **k):
        ips = answers[min(len(calls), len(answers) - 1)]
        calls.append(host)
        if ips is None:
            raise socket.gaierror("not found")
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))
                for ip in ips]
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    return calls


def test_only_global_addresses(monkeypatch):
    """Tailscale / CGNAT, a host that doesn't resolve, and a host with one local address among public ones: refused."""
    from tasks import from_link
    for ips in (["100.100.1.2"], ["100.64.0.1"], ["93.184.216.34", "10.0.0.5"], ["::ffff:127.0.0.1"], ["fd7a:115c::1"],
                ["192.0.2.1"], None, []):
        _answers(monkeypatch, ips)
        assert not from_link.public("https://shop.example/wine"), ips
    _answers(monkeypatch, ["93.184.216.34", "2606:2800:220:1::1"])
    assert from_link.public("https://shop.example/wine")


def test_connects_to_the_checked_address(monkeypatch):
    """The socket goes to the address checked at connection time: a second DNS answer pointing to the local network
    (DNS rebinding) is refused before anything connects there."""
    import socket
    import pytest
    from tasks import from_link
    connected = []

    def create_connection(address, *a, **k):
        connected.append(address)
        raise OSError("no network in tests")
    monkeypatch.setattr(socket, "create_connection", create_connection)

    # public at the check, local at the connection: refused, never connected
    _answers(monkeypatch, ["93.184.216.34"], ["192.168.1.2"])
    with pytest.raises(from_link.LinkError, match="local address"):
        from_link.fetch("http://shop.example/wine")
    assert connected == []

    # public both times: connected to that IP (not the hostname, which would be looked up again)
    _answers(monkeypatch, ["93.184.216.34"])
    with pytest.raises(from_link.LinkError, match="couldn't be reached"):
        from_link.fetch("https://shop.example:8443/wine")
    assert connected == [("93.184.216.34", 8443)]


def test_https_keeps_the_hostname(monkeypatch):
    """Pinned to the IP, a TLS connection still sends the hostname (SNI) and verifies the certificate against it."""
    import socket
    import ssl
    from tasks import from_link
    _answers(monkeypatch, ["93.184.216.34"])

    class Sock:
        def __init__(self, address):
            self.address = address

        def setsockopt(self, *a):
            pass
    monkeypatch.setattr(socket, "create_connection", lambda address, *a, **k: Sock(address))
    handler = from_link._PinnedHTTPS()
    assert handler._context.verify_mode == ssl.CERT_REQUIRED and handler._context.check_hostname
    conn = from_link._PinnedHTTPSConnection("shop.example", 443, context=handler._context)
    wrapped = {}
    monkeypatch.setattr(conn._context, "wrap_socket", lambda sock, server_hostname=None: wrapped.update(
        sock=sock, server_hostname=server_hostname) or sock, raising=False)
    conn.connect()
    assert wrapped["sock"].address == ("93.184.216.34", 443) and wrapped["server_hostname"] == "shop.example"
