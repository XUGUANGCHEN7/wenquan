"""Public tickets by day type with a payment-based validity window."""
from alembic import op
import sqlalchemy as sa

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ticket_batches") as batch:
        batch.alter_column("visit_date", existing_type=sa.Date(), nullable=True)
        batch.add_column(sa.Column("day_type", sa.String(16), nullable=True))
        batch.add_column(sa.Column("valid_days", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("valid_until", sa.DateTime(), nullable=True))


def downgrade():
    # Dateless orders cannot be converted to a truthful visit date.
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM ticket_batches WHERE visit_date IS NULL")).scalar():
        raise RuntimeError("Cannot downgrade while dateless public ticket orders exist")
    with op.batch_alter_table("ticket_batches") as batch:
        batch.drop_column("valid_until")
        batch.drop_column("valid_days")
        batch.drop_column("day_type")
        batch.alter_column("visit_date", existing_type=sa.Date(), nullable=False)
