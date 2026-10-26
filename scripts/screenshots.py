"""The README's screenshots, from a running app on a demo database (data/demo.db: a cellar to show, without personal
details), into screenshots/.

    DB_URL=sqlite:///../../data/demo.db GEO_DIR=../../data/geo uvicorn main:app --port 8020     # from app/api
    API_URL=http://localhost:8020 npx vite dev --port 5176                       # from app/web
    python scripts/screenshots.py [--base http://localhost:5176] [--only map,cellar]

Chrome (headless, through Selenium), dark theme, 1440 x 900 at twice the pixels, saved 1920 wide. Each shot: a page, what to do on it
(scroll to, click), how long the map or the network needs to settle.
"""
import argparse
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "screenshots")

# name: (path, JavaScript to run once loaded, seconds to wait after)
SHOTS = {
    # a region's page: its map fitted to the appellations you drink, the regions' bars
    "map": ("/regions/Bourgogne", None, 10),
    "wine": ("/wines/558", None, 8),
    "draw": ("/appellations/350", "const click = (t) => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === t).click();"
                                  " click('Draw outline'); setTimeout(() => click('Start from the official outline'), 4000)", 10),
    "cellar": ("/cellar?view=shelves", "document.querySelector('.panel.card').scrollIntoView({block: 'start'})", 3),
    "tastings": ("/tastings?period=all", None, 4),
    "grapes": ("/grapes?view=network&have=wines", "document.querySelector('.panel.card').scrollIntoView({block: 'start'})", 6),
    "grape": ("/grapes/3", "document.querySelector('.family')?.scrollIntoView({block: 'center'})", 4),
}


def shrink(path, width=1920):
    """Sharp on a retina screen, light in the repository: 1920 pixels wide, a palette of 256 colours."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:5176")
    parser.add_argument("--only", help="comma-separated names (default: all)")
    args = parser.parse_args()
    from selenium import webdriver
    opts = webdriver.ChromeOptions()
    for a in ("--headless=new", "--window-size=1440,900", "--force-device-scale-factor=2", "--hide-scrollbars"):
        opts.add_argument(a)
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark"}]})
    os.makedirs(OUT, exist_ok=True)
    try:
        for name, (path, js, wait) in SHOTS.items():
            if args.only and name not in args.only.split(","):
                continue
            driver.get(args.base + path)
            time.sleep(3)
            if js:
                driver.execute_script(js)
            time.sleep(wait)
            path = os.path.join(OUT, f"{name}.png")
            driver.save_screenshot(path)
            shrink(path)
            print(f"{name}.png")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
