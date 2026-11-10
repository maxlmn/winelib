"""A cellar tasting records whether it took the bottle out of the cellar, so deleting it can offer to put it back.
Existing notes: not known (NULL). Not 0011: that id is the pre-release databases' last revision, re-stamped as
0001 (migrate.SQUASHED), so a new 0011 would pass them as up to date.

Revision ID: 0012
"""
import sqlalchemy as sa
from alembic import op

revision = '0012'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tasting_notes') as batch:
        batch.add_column(sa.Column('took_bottle', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('tasting_notes') as batch:
        batch.drop_column('took_bottle')
