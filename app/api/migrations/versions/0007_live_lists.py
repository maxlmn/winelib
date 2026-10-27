"""Live lists: a list that keeps its criteria (tags, colour, region...) and shows what matches today

Revision ID: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('lists') as batch:
        batch.add_column(sa.Column('criteria', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('lists') as batch:
        batch.drop_column('criteria')
