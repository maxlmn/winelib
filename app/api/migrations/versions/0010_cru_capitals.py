"""Grand Cru and Premier Cru capitalised in appellation and vineyard names: INAO writes them in lower case ("Alsace
grand cru Brand", "Pommard premier cru Les Epenots"). A name only; an appellation whose capitalised name another
already has is left as it is.

Revision ID: 0010
"""
import re

import sqlalchemy as sa
from alembic import op

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

# as crus.cru_case (a migration keeps its own copy: the app's code may change after it)
CRU_WORDS = re.compile(r"\b([Gg]rand|[Pp]remier|1er) cru\b")


def cru_case(name):
    return CRU_WORDS.sub(lambda m: f"{m.group(1).capitalize()} Cru", name)


def upgrade():
    conn = op.get_bind()
    for table, unique in (("appellations", True), ("vineyards", False)):
        rows = conn.execute(sa.text(f"SELECT id, name FROM {table} WHERE name IS NOT NULL")).all()
        taken = {name for _, name in rows}
        for id_, name in rows:
            new = cru_case(name)
            if new == name or (unique and new in taken):
                continue
            conn.execute(sa.text(f"UPDATE {table} SET name = :n WHERE id = :i"), {"n": new, "i": id_})
            taken.add(new)


def downgrade():
    pass  # a spelling: nothing in the schema to undo
