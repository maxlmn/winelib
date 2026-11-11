"""The app has no login, so it trusts its network; a web page elsewhere can still reach it through the visitor's
browser by pointing a name of its own at the app's address (DNS rebinding). The browser then sends that name as
the Host, so a request is answered only when its Host is one a home installation goes by:

- an IP address, localhost, a name without a dot (nas, jupiter);
- a name of a home or private network: .local, .lan, .home, .home.arpa, .internal, .localhost, and Tailscale's
  .ts.net;
- the names in WINELIB_HOSTS (comma-separated: wine.example.com; "*.example.com" for its sub-domains; "*" for any
  name, behind a proxy that checks it itself).

Anything else gets a 403 saying so.
"""
import ipaddress
import os

SUFFIXES = (".local", ".lan", ".home", ".home.arpa", ".internal", ".localhost", ".ts.net")


def configured():
    return [h.strip().lower() for h in os.getenv("WINELIB_HOSTS", "").split(",") if h.strip()]


def name_of(host):
    """The Host header without its port: "nas:8000" -> "nas", "[::1]:8000" -> "::1"."""
    host = (host or "").strip().lower()
    if host.startswith("["):
        return host[1:].split("]")[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def allowed(host, extra=None):
    name = name_of(host).rstrip(".")
    extra = configured() if extra is None else extra
    if "*" in extra:
        return True
    if not name:
        return False
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    if "." not in name or name.endswith(SUFFIXES):
        return True
    return any(name == h or (h.startswith("*.") and name.endswith(h[1:])) for h in extra)


class HostCheck:
    """A plain ASGI middleware (as StoreFresh: no "No response returned" for a request a browser abandons)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            host = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"host"), "")
            if not allowed(host):
                body = (f"WineLib doesn't answer to the name {name_of(host) or '(none)'}.\n"
                        "Reach it by its IP address or local name, or add this name to WINELIB_HOSTS "
                        "(see .secrets.env.example) and restart it.\n").encode()
                await send({"type": "http.response.start", "status": 403,
                            "headers": [(b"content-type", b"text/plain; charset=utf-8"), (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)
