"""Lists: of wines, cuvées and producers to find and taste

Revision ID: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('lists',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('created', sa.Date(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('list_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('list_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('wine_id', sa.Integer(), nullable=True),
    sa.Column('producer_id', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['list_id'], ['lists.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['producer_id'], ['producers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['wine_id'], ['wines.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_list_items_list_id'), 'list_items', ['list_id'], unique=False)
    op.create_index(op.f('ix_list_items_producer_id'), 'list_items', ['producer_id'], unique=False)
    op.create_index(op.f('ix_list_items_wine_id'), 'list_items', ['wine_id'], unique=False)


def downgrade():
    op.drop_table('list_items')
    op.drop_table('lists')
