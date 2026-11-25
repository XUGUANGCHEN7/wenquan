"""Persist idempotent per-order batch admission results."""
from alembic import op
import sqlalchemy as sa

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("admission_batches"):
        op.create_table("admission_batches",
            sa.Column("request_id", sa.String(64), primary_key=True),
            sa.Column("order_id", sa.String(64), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("ticket_nos", sa.JSON(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("admitted_at", sa.DateTime(), nullable=False))


def downgrade():
    if sa.inspect(op.get_bind()).has_table("admission_batches"):
        op.drop_table("admission_batches")
