"""Critics' scores as the lists show them: initials and score, "RP 95 · VI 94" (the preferred critic first, then the
others by name; "-", searched and none found, left out)."""
import re
from collections import defaultdict

from db import CriticScore


def initials(critic):
    """"Robert Parker" -> "RP", "Jancis Robinson" -> "JR", "Vinous" -> "VI"."""
    words = re.findall(r"[^\W\d_]+", critic or "")
    if not words:
        return "?"
    return (words[0][0] + words[1][0] if len(words) > 1 else words[0][:2]).upper()


def real(score):
    return bool(score) and score.strip() not in ("", "-", "0", "None")


def label(scores):
    """The text for (critic, score) pairs or CriticScore rows: "RP 95 · VI 94", or None."""
    pairs = [(s.critic, s.score) if isinstance(s, CriticScore) else s for s in scores]
    first = preferred().lower()
    pairs = sorted((p for p in pairs if real(p[1])), key=lambda p: (p[0].lower() != first, p[0].lower()))
    return " · ".join(f"{initials(c)} {s.strip()}" for c, s in pairs) or None


def preferred():
    import settings
    return settings.current.preferred_critic


def preferred_score(scores):
    """The preferred critic's score among a wine's CriticScore rows (Settings), or None."""
    critic = preferred().lower()
    return next((s.score.strip() for s in scores if s.critic.lower() == critic and real(s.score)), None)


def number(score):
    """A score as a number, for sorting: "95", "95+", "(95-97)" -> 95; "17.5" -> 17.5; None without one."""
    m = re.search(r"\d+(?:\.\d+)?", score or "")
    return float(m.group()) if m else None


def listing(scores):
    """A wine's CriticScore rows for its pages, the preferred critic first, then by name:
    [{"critic", "score", "note", "url", "date"}] ("-", searched and none found, kept: the page offers a search)."""
    first = preferred().lower()
    return [{"critic": s.critic, "score": s.score, "note": s.note, "url": s.url,
             "date": s.date.isoformat() if s.date else None}
            for s in sorted(scores, key=lambda s: (s.critic.lower() != first, s.critic.lower()))]


def labels(session, wine_ids):
    """{wine_id: label} for these wines (one query)."""
    ids = list(set(wine_ids))
    if not ids:
        return {}
    by_wine = defaultdict(list)
    for wid, critic, score in (session.query(CriticScore.wine_id, CriticScore.critic, CriticScore.score)
                               .filter(CriticScore.wine_id.in_(ids))):
        by_wine[wid].append((critic, score))
    return {wid: label(pairs) for wid, pairs in by_wine.items()}
