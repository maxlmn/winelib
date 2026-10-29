"""The Lyonnais in neither the Rhône nor the Beaujolais (0008 had put it in the Rhône): Coteaux du Lyonnais, its wines
and their vineyards, and the producers of "The Lyonnais", filed under France. Nothing when a database has no France
or no Rhône region.

Revision ID: 0009
"""
import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    one = lambda sql, **p: conn.execute(sa.text(sql), p).scalar()  # noqa: E731
    france = one("SELECT id FROM regions WHERE lower(name) = 'france'")
    rhone = one("SELECT id FROM regions WHERE lower(name) IN ('rhone', 'rhône')")
    if not france or not rhone:
        return
    apps = [r[0] for r in conn.execute(sa.text(
        "SELECT id FROM appellations WHERE region_id = :rhone AND lower(replace(name, '-', ' ')) = 'coteaux du lyonnais'"),
        {"rhone": rhone})]
    p = {"france": france, "rhone": rhone}
    for a in apps:
        conn.execute(sa.text("UPDATE vineyards SET region_id = :france WHERE region_id = :rhone AND id IN "
                             "(SELECT vineyard_id FROM wines WHERE appellation_id = :a)"), {**p, "a": a})
        conn.execute(sa.text("UPDATE wines SET region_id = :france WHERE region_id = :rhone AND appellation_id = :a"),
                     {**p, "a": a})
        conn.execute(sa.text("UPDATE appellations SET region_id = :france WHERE id = :a"), {**p, "a": a})
    conn.execute(sa.text("UPDATE producers SET region_id = :france WHERE region_id = :rhone AND subregion = 'The Lyonnais'"), p)


def downgrade():
    pass  # the data stays in France: nothing in the schema to undo
