"""The website's read-only demo from a demo database: the app run on it (alone: no key, no other database), the
published map pack installed, every page crawled in Chromium and its API answers saved (app/web/scripts/
crawl-demo.mjs), and the app built read-only for the demo's address (VITE_DEMO=1). Writes a zip the website's
workflow unpacks at /demo/. Run by .github/workflows/demo.yml at each release, or by hand:

    python scripts/build_demo.py --db demo.db --out dist/winelib-demo.zip

Needs the app's packages (app/api/requirements.txt), the web app's (app/web: npm ci) and Chromium (npx playwright
install chromium). The database is copied: the original is never changed.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "app", "web")
PACK_URL = "https://github.com/maxlmn/winelib/releases/download/map-pack/winelib-map-pack.zip"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def call(url, body=None):
    req = urllib.request.Request(url, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def run(cmd, **kw):
    print("$", re.sub(r"://([^:/@]+):[^@]+@", r"://\1:***@", " ".join(cmd)), flush=True)  # no password in the log
    subprocess.run(cmd, check=True, **kw)


def build(db, out, base="/winelib/demo", pack=PACK_URL, max_pages=6000, tabs=6, keep=False):
    npm, node = shutil.which("npm"), shutil.which("node")
    if not (npm and node):
        sys.exit("Needs Node.js (npm)")
    work = tempfile.mkdtemp(prefix="winelib-demo-")
    data, site = os.path.join(work, "data"), os.path.join(work, "demo")
    os.makedirs(data)
    shutil.copy(db, os.path.join(data, "winelib.db"))
    print("work folder:", work, flush=True)
    try:
        # The app on the demo database, alone, with the web app built as it ships (what the crawler opens)
        if not os.path.exists(os.path.join(WEB, "build", "index.html")):
            run([npm, "run", "build"], cwd=WEB)
        port = free_port()
        keep_env = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                    "PYTHONIOENCODING", "VIRTUAL_ENV", "pythonLocation", "LD_LIBRARY_PATH")
        env = {k: v for k, v in os.environ.items() if k in keep_env}
        env.update(DB_URL=f"sqlite:///{os.path.join(data, 'winelib.db')}", MAP_PACK_URL=pack)
        server = subprocess.Popen([sys.executable, os.path.join(ROOT, "run.py"), "--data", data, "--port", str(port),
                                   "--no-browser"], env=env, cwd=ROOT)
        url = f"http://127.0.0.1:{port}"
        try:
            for _ in range(180):
                try:
                    call(url + "/api/settings")
                    break
                except OSError:
                    time.sleep(1)
            else:
                sys.exit("The app didn't start")
            # The published map pack, installed and linked
            call(url + "/api/maintenance/map_pack", {"commit": True})
            while (job := call(url + "/api/maintenance/job")).get("status") == "running":
                time.sleep(3)
            print("map pack:", (job.get("result") or {}).get("summary") or job.get("status"), flush=True)
            if job.get("status") != "done":
                sys.exit("The map pack wasn't installed")
            # Every page, its API answers saved
            run([node, os.path.join(WEB, "scripts", "crawl-demo.mjs"), "--url", url, "--out",
                 os.path.join(site, "demo-data"), "--max", str(max_pages), "--tabs", str(tabs)], cwd=WEB)
        finally:
            server.terminate()
            server.wait(30)

        # The app, read-only, for the demo's address (its own build folder: build/ stays the app's)
        web = os.path.join(work, "web")
        run([npm, "run", "build"], cwd=WEB, env={**os.environ, "BASE_PATH": base, "VITE_DEMO": "1", "BUILD_DIR": web})
        shutil.copytree(web, site, dirs_exist_ok=True)
        # Pages serves 404.html for the app's routes; the demo's own address gets the same page as index.html
        shutil.copy(os.path.join(site, "404.html"), os.path.join(site, "index.html"))

        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        zip_path = shutil.make_archive(os.path.splitext(os.path.abspath(out))[0], "zip", site)
        print(f"{zip_path}: {os.path.getsize(zip_path) / 1e6:.1f} MB", flush=True)
        return zip_path
    finally:
        if keep:
            print("kept:", work)
        else:
            shutil.rmtree(work, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, help="the demo database (SQLite), e.g. the release tagged demo's")
    parser.add_argument("--out", default=os.path.join(ROOT, "dist", "winelib-demo.zip"))
    parser.add_argument("--base", default="/winelib/demo", help="the demo's address on the website")
    parser.add_argument("--pack", default=PACK_URL, help="the map pack (an https address or a file)")
    parser.add_argument("--max", type=int, default=20000, help="pages to open at most (every page: about 8,500 for the demo cellar)")
    parser.add_argument("--tabs", type=int, default=6, help="pages open at once")
    parser.add_argument("--keep", action="store_true", help="keep the work folder")
    a = parser.parse_args()
    build(a.db, a.out, a.base, a.pack, a.max, a.tabs, a.keep)


if __name__ == "__main__":
    main()
