"""France's regions: the Lyonnais is part of the Rhône, and the Beaujolais has its own colour.

- The Lyonnais' appellation (Coteaux du Lyonnais), wines, producers and vineyards move to the Rhône region, the
  appellation with the sub-region "The Lyonnais" (as its producers already had), and the Lyonnais region goes; a live
  list on it now lists the Rhône. Nothing when a database has no Lyonnais or no Rhône region.
- The Beaujolais had Bourgogne's pink: it takes its violet, unless its colour was changed here.

Revision ID: 0008
"""
import json

import sqlalchemy as sa
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

SHARED_PINK, BEAUJOLAIS = "#d97693", "#9a7bc9"


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE regions SET color = :new WHERE lower(name) = 'beaujolais' AND lower(color) = :old"),
                 {"new": BEAUJOLAIS, "old": SHARED_PINK})
    _lyonnais_into_rhone(conn)


def _lyonnais_into_rhone(conn):
    ids = lambda names: [r[0] for r in conn.execute(
        sa.text("SELECT id FROM regions WHERE lower(name) IN :n").bindparams(sa.bindparam("n", expanding=True)),
        {"n": names})]
    lyonnais, rhone = ids(["lyonnais"]), ids(["rhone", "rhône"])
    if not lyonnais or not rhone:
        return
    old, new = lyonnais[0], rhone[0]
    conn.execute(sa.text("UPDATE appellations SET subregion = 'The Lyonnais' WHERE region_id = :old "
                         "AND (subregion IS NULL OR subregion = '')"), {"old": old})
    for table in ("appellations", "wines", "producers", "vineyards"):
        conn.execute(sa.text(f"UPDATE {table} SET region_id = :new WHERE region_id = :old"), {"old": old, "new": new})
    rhone_name = conn.execute(sa.text("SELECT name FROM regions WHERE id = :id"), {"id": new}).scalar()
    for lid, criteria in conn.execute(sa.text("SELECT id, criteria FROM lists WHERE criteria IS NOT NULL")).fetchall():
        try:
            c = json.loads(criteria)
        except ValueError:
            continue
        regions = c.get("regions") if isinstance(c, dict) else None
        if regions and any(str(r).lower() == "lyonnais" for r in regions):
            c["regions"] = list(dict.fromkeys(rhone_name if str(r).lower() == "lyonnais" else r for r in regions))
            conn.execute(sa.text("UPDATE lists SET criteria = :c WHERE id = :id"), {"c": json.dumps(c), "id": lid})
    conn.execute(sa.text("DELETE FROM regions WHERE id = :old"), {"old": old})


def downgrade():
    pass  # the data stays in the Rhône: nothing in the schema to undo
