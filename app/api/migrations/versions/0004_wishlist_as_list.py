"""The wishlist becomes a list: its entries move to a list flagged as the wishlist, its table goes

An entry for any vintage becomes a cuvée entry, the others a wine entry; its note, the shop's link and a size other
than 75 cl go in the entry's note. The wishlist's market prices aren't kept (lists don't price their wines).

Revision ID: 0004
"""
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('lists') as batch:
        batch.add_column(sa.Column('is_wishlist', sa.Boolean(), nullable=False, server_default=sa.false()))
    conn = op.get_bind()
    if 'wishlist' not in sa.inspect(conn).get_table_names():
        return
    rows = conn.execute(sa.text(
        "SELECT w.wine_id, w.any_vintage, w.bottle_size, w.note, w.url, wines.producer_id FROM wishlist w "
        "JOIN wines ON wines.id = w.wine_id ORDER BY w.added, w.id")).fetchall()
    if rows:
        found = conn.execute(sa.text("SELECT id FROM lists WHERE lower(name) = 'wishlist'")).first()
        if found:
            list_id = found[0]
            conn.execute(sa.text("UPDATE lists SET is_wishlist = :t WHERE id = :i"), {"t": True, "i": list_id})
        else:
            conn.execute(sa.text("INSERT INTO lists (name, description, created, is_wishlist) VALUES "
                                 "('Wishlist', 'Wines you’d like', :d, :t)"), {"d": date.today(), "t": True})
            list_id = conn.execute(sa.text("SELECT id FROM lists WHERE name = 'Wishlist'")).first()[0]
        start = conn.execute(sa.text("SELECT coalesce(max(position), 0) FROM list_items WHERE list_id = :i"),
                             {"i": list_id}).scalar()
        for n, (wine_id, any_vintage, size, note, url, producer_id) in enumerate(rows, start + 1):
            parts = [note, url, size if size and size.replace(" ", "").lower() != "75cl" else None]
            conn.execute(sa.text(
                "INSERT INTO list_items (list_id, kind, wine_id, producer_id, note, position) "
                "VALUES (:l, :k, :w, :p, :n, :pos)"),
                {"l": list_id, "k": "cuvee" if any_vintage else "wine", "w": wine_id, "p": producer_id,
                 "n": " · ".join(x for x in parts if x) or None, "pos": n})
    op.drop_table('wishlist')


def downgrade():
    with op.batch_alter_table('lists') as batch:
        batch.drop_column('is_wishlist')
