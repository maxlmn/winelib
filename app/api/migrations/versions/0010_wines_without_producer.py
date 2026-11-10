"""Every wine has a producer: a wine left without one (by an import of an earlier version) gets "Unknown producer",
made when needed, so its pages open (a vintage page with it failed) and it can be fixed or deleted. Nothing when
every wine has its producer.

Revision ID: 0010
"""
import sqlalchemy as sa
from alembic import op

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

NAME = "Unknown producer"


def upgrade():
    conn = op.get_bind()
    orphans = "SELECT id FROM wines WHERE producer_id IS NULL OR producer_id NOT IN (SELECT id FROM producers)"
    if conn.execute(sa.text(orphans)).first() is None:
        return
    pid = conn.execute(sa.text("SELECT id FROM producers WHERE name = :n"), {"n": NAME}).scalar()
    if pid is None:
        conn.execute(sa.text("INSERT INTO producers (name) VALUES (:n)"), {"n": NAME})
        pid = conn.execute(sa.text("SELECT id FROM producers WHERE name = :n"), {"n": NAME}).scalar()
    conn.execute(sa.text(f"UPDATE wines SET producer_id = :p WHERE id IN ({orphans})"), {"p": pid})


def downgrade():
    pass  # which wines had no producer isn't kept: they keep "Unknown producer"
