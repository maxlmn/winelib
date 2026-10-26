"""Help: short guides to WineLib's features, one Markdown file each in app/api/data/docs/help/ ("01-first-steps.md":
its order, then its address). A guide's title is its first heading, its summary the paragraph after it."""
import os
import re

from fastapi import APIRouter, HTTPException

router = APIRouter()

HELP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "docs", "help")


def _guides():
    """[(slug, path)] in order."""
    names = sorted(f for f in os.listdir(HELP) if f.endswith(".md")) if os.path.isdir(HELP) else []
    return [(re.sub(r"^\d+-", "", f[:-3]), os.path.join(HELP, f)) for f in names]


def _read(path):
    """(title, summary, the rest as Markdown)"""
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    first, _, rest = text.partition("\n")
    title = first.lstrip("# ").strip()
    summary = rest.strip().split("\n\n")[0].strip() if rest.strip() and not rest.strip().startswith("#") else ""
    body = rest.strip()[len(summary):].strip() if summary else rest.strip()
    return title, summary, body


@router.get("/api/help")
def guides():
    out = []
    for slug, path in _guides():
        title, summary, _ = _read(path)
        out.append({"slug": slug, "title": title, "summary": summary})
    return out


@router.get("/api/help/{slug}")
def guide(slug: str):
    order = _guides()
    i = next((n for n, (s, _) in enumerate(order) if s == slug), None)
    if i is None:
        raise HTTPException(404, "No such guide")
    title, summary, body = _read(order[i][1])
    near = lambda n: {"slug": order[n][0], "title": _read(order[n][1])[0]} if 0 <= n < len(order) else None  # noqa: E731
    return {"slug": slug, "title": title, "summary": summary, "body": body, "prev": near(i - 1), "next": near(i + 1)}
