"""Reliefs: the contour lines inside each vineyard's outline (relief.py), for the maps.

Revision ID: 0016
"""
import sqlalchemy as sa
from alembic import op

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('reliefs', sa.Column('contours', sa.Text()))


def downgrade():
    op.drop_column('reliefs', 'contours')
