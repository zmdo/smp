"""virtual cards

Revision ID: 004
Revises: 003
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "virtual_cards" not in set(inspector.get_table_names()):
        op.create_table(
            "virtual_cards",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("holder", sa.String(80), nullable=False),
            sa.Column("expiry", sa.String(5), nullable=False),
            sa.Column("last4", sa.String(4), nullable=False),
            sa.Column("number_ciphertext", sa.Text(), nullable=False),
            sa.Column("cvv_ciphertext", sa.Text(), nullable=False),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if bind.dialect.name == "postgresql":
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON virtual_cards TO web_api")


def downgrade() -> None:
    op.drop_table("virtual_cards")
