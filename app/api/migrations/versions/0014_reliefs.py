"""Reliefs: a vineyard outline's elevation, slope and aspect (relief.py), worked out once from open terrain tiles.

Revision ID: 0014
"""
import sqlalchemy as sa
from alembic import op

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'reliefs',
        sa.Column('boundary', sa.String(), primary_key=True),
        sa.Column('elevation_min', sa.Float(), nullable=False),
        sa.Column('elevation_mean', sa.Float(), nullable=False),
        sa.Column('elevation_max', sa.Float(), nullable=False),
        sa.Column('slope_median', sa.Float(), nullable=False),
        sa.Column('slope_steep', sa.Float(), nullable=False),
        sa.Column('aspect', sa.Float()),
        sa.Column('zoom', sa.Integer(), nullable=False),
        sa.Column('computed', sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table('reliefs')
