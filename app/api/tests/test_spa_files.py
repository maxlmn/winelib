"""The web build's files are served, nothing outside it (main.build_file)."""
import os

from main import build_file


def seed(session):
    """No data: only the app's routes"""


def test_only_the_builds_files(tmp_path):
    build = tmp_path / "build"
    (build / "_app").mkdir(parents=True)
    (build / "index.html").write_text("app")
    (build / "_app" / "x.js").write_text("js")
    (tmp_path / "secret.env").write_text("password")
    assert build_file(str(build), "index.html") == os.path.realpath(build / "index.html")
    assert build_file(str(build), "_app/x.js") == os.path.realpath(build / "_app" / "x.js")
    assert build_file(str(build), "") is None
    assert build_file(str(build), "missing.html") is None
    # outside the build: refused, however written
    for path in ("../secret.env", "_app/../../secret.env", r"..\secret.env", str(tmp_path / "secret.env"),
                 "C:/Windows/win.ini", "/etc/passwd"):
        assert build_file(str(build), path) is None, path


def test_the_route_refuses_traversal(client):
    """Through the app: an encoded "../" gets the app's page (or a 404 without a build), never the file."""
    for url in ("/..%2f..%2fapi%2fpaths.py", "/%2e%2e/%2e%2e/api/paths.py", "/..%2f..%2f..%2f..%2f.gitignore"):
        r = client.get(url)
        assert "Where the app keeps its files" not in r.text and ".venv" not in r.text, url
