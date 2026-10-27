"""Style tags: set on a wine, or picked in a tasting ("fresh", "mineral")

Revision ID: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('wine_tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('wine_id', sa.Integer(), nullable=False),
    sa.Column('tag', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['wine_id'], ['wines.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('wine_id', 'tag')
    )
    op.create_index(op.f('ix_wine_tags_wine_id'), 'wine_tags', ['wine_id'], unique=False)
    op.create_table('tasting_tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tasting_id', sa.Integer(), nullable=False),
    sa.Column('tag', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['tasting_id'], ['tasting_notes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tasting_id', 'tag')
    )
    op.create_index(op.f('ix_tasting_tags_tasting_id'), 'tasting_tags', ['tasting_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_tasting_tags_tasting_id'), table_name='tasting_tags')
    op.drop_table('tasting_tags')
    op.drop_index(op.f('ix_wine_tags_wine_id'), table_name='wine_tags')
    op.drop_table('wine_tags')
