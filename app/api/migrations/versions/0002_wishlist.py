"""The wishlist

Revision ID: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('wishlist',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('wine_id', sa.Integer(), nullable=False),
    sa.Column('any_vintage', sa.Boolean(), nullable=False),
    sa.Column('bottle_size', sa.String(), nullable=True),
    sa.Column('target_price', sa.Float(), nullable=True),
    sa.Column('currency', sa.String(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('added', sa.Date(), nullable=True),
    sa.Column('last_price', sa.Float(), nullable=True),
    sa.Column('last_price_date', sa.Date(), nullable=True),
    sa.Column('last_price_source', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['wine_id'], ['wines.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('wine_id')
    )


def downgrade():
    op.drop_table('wishlist')
