"""Persist member refund applications and review decisions."""
from alembic import op
import sqlalchemy as sa

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("refund_applications"):
        op.create_table("refund_applications",
            sa.Column("order_id", sa.String(64), sa.ForeignKey("orders.id"), primary_key=True),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("review_reason", sa.Text(), nullable=False),
            sa.Column("reviewed_by", sa.String(96), nullable=True),
            sa.Column("refund_no", sa.String(80), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True))


def downgrade():
    if sa.inspect(op.get_bind()).has_table("refund_applications"):
        op.drop_table("refund_applications")
