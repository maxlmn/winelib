"""Reliefs: a marker for an outline with nothing to work out (too big, too small, no outline in the store), so the
page and the Maintenance task don't fetch its terrain again and again (routers/relief.py).

Revision ID: 0018
"""
import sqlalchemy as sa
from alembic import op

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('reliefs', sa.Column('none_reason', sa.String()))


def downgrade():
    op.drop_column('reliefs', 'none_reason')
