"""Geologies: a vineyard outline's rock from Macrostrat (outside France), asked once and kept (geology.py).

Revision ID: 0015
"""
import sqlalchemy as sa
from alembic import op

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'geologies',
        sa.Column('boundary', sa.String(), primary_key=True),
        sa.Column('data', sa.Text(), nullable=False),
        sa.Column('computed', sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table('geologies')
