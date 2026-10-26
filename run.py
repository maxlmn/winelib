"""Runs WineLib on this computer: http://127.0.0.1:8000, opened in your browser.

    pip install -r app/api/requirements.txt      # once (Python 3.11 or newer)
    python run.py                                # Ctrl+C to stop

Your data (database, photos, backups, plug-ins) is kept in your user folder, apart from the program, so a newer
version unzipped elsewhere finds it: ~/.local/share/winelib (Linux), ~/Library/Application Support/winelib (macOS),
%APPDATA%\\winelib (Windows). --data names another folder. In a git checkout (developers), data/ in the checkout.

    python run.py --port 8080 --no-browser
    python run.py --host 0.0.0.0     # reachable from other machines: only behind your own sign-in (see README)
"""
import argparse
import os
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(ROOT, "app", "api")
WEB_BUILD = os.path.join(ROOT, "app", "web", "build")


def user_data_dir(name="winelib"):
    if sys.platform == "win32":
        return os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), name)
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", name)
    return os.path.join(os.getenv("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"), name)


def check():
    """What's missing to run, or None."""
    if sys.version_info < (3, 11):
        return f"WineLib needs Python 3.11 or newer (this is {sys.version.split()[0]})."
    try:
        import alembic, fastapi, sqlalchemy, uvicorn  # noqa: E401,F401
    except ImportError as e:
        return f"A package is missing ({e.name}): pip install -r {os.path.relpath(os.path.join(API_DIR, 'requirements.txt'))}"
    if not os.path.isfile(os.path.join(WEB_BUILD, "index.html")):
        return ("The web app isn't built (app/web/build/). Download the release zip, which has it, or build it with "
                "Node.js: cd app/web && npm install && npm run build")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1", help="127.0.0.1 (this computer only) by default")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data", help="the folder for your data (default: your user folder)")
    parser.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = parser.parse_args()
    problem = check()
    if problem:
        sys.exit(problem)
    if args.data:
        os.environ["WINELIB_DATA"] = os.path.abspath(args.data)
    elif not os.path.isdir(os.path.join(ROOT, ".git")) and not os.getenv("DB_URL"):
        os.environ.setdefault("WINELIB_DATA", user_data_dir())  # a release unzipped: data apart from the program
    os.environ.setdefault("WEB_BUILD", WEB_BUILD)
    sys.path.insert(0, API_DIR)
    import uvicorn

    import paths
    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}"
    print(f"WineLib: {url}  (data: {paths.DATA_DIR}; Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("main:app", host=args.host, port=args.port, app_dir=API_DIR, log_level="warning")


if __name__ == "__main__":
    main()
