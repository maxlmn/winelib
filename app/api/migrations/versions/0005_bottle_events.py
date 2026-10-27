"""Bottle events: bottles gifted, sold or broken (not only drunk)

Revision ID: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('bottle_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bottle_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('qty', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('price', sa.Float(), nullable=True),
    sa.Column('currency', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['bottle_id'], ['cellar.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bottle_events_bottle_id'), 'bottle_events', ['bottle_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_bottle_events_bottle_id'), table_name='bottle_events')
    op.drop_table('bottle_events')
