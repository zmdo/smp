"""mcp settings

Revision ID: 007
Revises: 006
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("token_hash", sa.String(64)),
        sa.Column("token_last4", sa.String(8)),
        sa.Column("expose_servers", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expose_wallets", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expose_cards", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("GRANT SELECT, INSERT, UPDATE ON mcp_settings TO web_api")


def downgrade() -> None:
    op.drop_table("mcp_settings")
