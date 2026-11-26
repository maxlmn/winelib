"""Roussette is Altesse: the grape list had a separate "Roussette" (VIVC 10264, an unrelated variety) where Savoie's
Roussette, Altesse, was meant (Roussette de Savoie, Roussette du Bugey). Its wines move to Altesse (their main grape
and their grape list, never a grape twice on a wine), Altesse takes the fields it lacked and "Roussette" among its
aliases, and the stray grape is deleted. A database without Altesse has the row renamed instead.

Revision ID: 0017
"""
from alembic import op
from sqlalchemy import text

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None

FIELDS = ["color", "origin", "parents", "climate", "depth", "acidity", "acid_shape", "acid_type", "tannin",
          "tannin_type", "tannin_location", "aromas", "notes", "classic_regions"]
ALIASES = ["Roussette", "Roussette de Savoie"]


def merge(conn):
    """The move itself, on a connection (the tests call it)"""
    stray = conn.execute(text("SELECT id FROM varietals WHERE name = 'Roussette' AND (vivc = 10264 OR vivc IS NULL)")).first()
    if stray is None:
        return
    stray = stray[0]
    altesse = conn.execute(text("SELECT id, aliases FROM varietals WHERE name = 'Altesse'")).first()
    if altesse is None:
        conn.execute(text("UPDATE varietals SET name = 'Altesse', vivc = 354, aliases = :a WHERE id = :r"),
                     {"a": ", ".join(ALIASES), "r": stray})
        return
    keep, aliases = altesse
    p = {"r": stray, "k": keep}
    conn.execute(text("UPDATE wines SET varietal_id = :k WHERE varietal_id = :r"), p)
    conn.execute(text("DELETE FROM wine_grapes WHERE varietal_id = :r AND wine_id IN "
                      "(SELECT wine_id FROM wine_grapes WHERE varietal_id = :k)"), p)
    conn.execute(text("UPDATE wine_grapes SET varietal_id = :k WHERE varietal_id = :r"), p)
    for f in FIELDS:
        conn.execute(text(f"UPDATE varietals SET {f} = (SELECT {f} FROM varietals WHERE id = :r) "
                          f"WHERE id = :k AND ({f} IS NULL OR {f} = '')"), p)
    names = [a.strip() for a in (aliases or "").split(",") if a.strip()]
    names += [a for a in ALIASES if a.lower() not in {n.lower() for n in names}]
    conn.execute(text("UPDATE varietals SET aliases = :a WHERE id = :k"), {"a": ", ".join(names), "k": keep})
    conn.execute(text("DELETE FROM varietals WHERE id = :r"), p)


def upgrade():
    merge(op.get_bind())


def downgrade():
    pass  # the stray grape isn't brought back
