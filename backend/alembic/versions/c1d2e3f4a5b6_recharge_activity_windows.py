"""Add optional recharge activity date windows."""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = 'b72e91c4a103'
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table('recharge_activity_windows'):
        op.create_table(
            'recharge_activity_windows',
            sa.Column('activity_id', sa.String(length=64), sa.ForeignKey('recharge_activities.id'), primary_key=True),
            sa.Column('starts_on', sa.Date(), nullable=True),
            sa.Column('ends_on', sa.Date(), nullable=True),
        )


def downgrade():
    if sa.inspect(op.get_bind()).has_table('recharge_activity_windows'):
        op.drop_table('recharge_activity_windows')
