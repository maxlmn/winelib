"""The composed pictures of the README and the website, from what app/web/scripts/screenshots.mjs took (in
screenshots/): the three phone shots in their frames (mobile.png), the home page in light and in dark side by side
(themes.png), the walk-through's frames as a GIF (demo.gif), each in light and in dark. Then the raw phone shots and
the frames are removed.

    python scripts/screenshots_compose.py [screenshots]

Needs Pillow (app/api/requirements.txt has it).
"""
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def phones(folder, dark):
    """Three phones side by side on the page's ground: home, the cellar, a wine."""
    suffix = "-dark" if dark else ""
    ground = (26, 23, 28) if dark else (247, 244, 242)
    shots = [Image.open(os.path.join(folder, f"phone-{n}{suffix}.png")).convert("RGB") for n in ("home", "cellar", "wine")]
    w, h = 530, 1087  # a shot (780 x 1600) scaled into its phone
    bezel, gap, top = 14, 60, 70
    sheet = Image.new("RGB", (1920, h + 2 * bezel + 2 * top), ground)
    draw = ImageDraw.Draw(sheet)
    x = (1920 - 3 * (w + 2 * bezel) - 2 * gap) // 2
    for shot in shots:
        draw.rounded_rectangle([x, top, x + w + 2 * bezel, top + h + 2 * bezel], radius=54, fill=(12, 12, 14))
        screen = shot.resize((w, h), Image.LANCZOS)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=42, fill=255)
        sheet.paste(screen, (x + bezel, top + bezel), mask)
        x += w + 2 * bezel + gap
    sheet.save(os.path.join(folder, f"mobile{suffix}.png"), optimize=True)


def themes(folder):
    """The home page in light and in dark, side by side."""
    light, dark = (Image.open(os.path.join(folder, f)).convert("RGB") for f in ("home.png", "home-dark.png"))
    w = 940
    h = round(light.height * w / light.width)
    sheet = Image.new("RGB", (1920, h + 8), (255, 255, 255))
    sheet.paste(light.resize((w, h), Image.LANCZOS), (10, 4))
    sheet.paste(dark.resize((w, h), Image.LANCZOS), (970, 4))
    sheet.save(os.path.join(folder, "themes.png"), optimize=True)


def clip(folder, dark):
    """The walk-through's frames as one GIF, each frame for the time it was given."""
    src = os.path.join(folder, "clip", "dark" if dark else "light")
    with open(os.path.join(src, "frames.json"), encoding="utf-8") as f:
        frames = json.load(f)
    images = [Image.open(os.path.join(src, fr["file"])).convert("RGB") for fr in frames]
    # one palette for the whole clip (the first frames' colours), so the frames don't flicker
    palette = images[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    quantized = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
    quantized[0].save(os.path.join(folder, f"demo{'-dark' if dark else ''}.gif"), save_all=True, append_images=quantized[1:],
                      duration=[fr["ms"] for fr in frames], loop=0, optimize=True)


def main(folder):
    for dark in (False, True):
        phones(folder, dark)
        clip(folder, dark)
    themes(folder)
    for name in os.listdir(folder):  # what the composed pictures were made from
        if name.startswith("phone-"):
            os.remove(os.path.join(folder, name))
    shutil.rmtree(os.path.join(folder, "clip"), ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "screenshots"))
