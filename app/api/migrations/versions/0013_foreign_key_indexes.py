"""Indexes on the columns pages join and count by: a wine's bottles, a bottle's tastings, a place's, a day's, the
wines of an appellation, a region, a vineyard, a grape. Without them each of those read the whole table (on Postgres
above all, and in the checks before a delete).

Revision ID: 0013
"""
from alembic import op

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None

INDEXES = [
    ("cellar", "wine_id"),
    ("tasting_notes", "bottle_id"),
    ("tasting_notes", "place_id"),
    ("tasting_notes", "date"),
    ("wines", "appellation_id"),
    ("wines", "region_id"),
    ("wines", "vineyard_id"),
    ("wines", "varietal_id"),
]


def upgrade():
    for table, column in INDEXES:
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table, column in INDEXES:
        op.drop_index(f"ix_{table}_{column}", table_name=table)
