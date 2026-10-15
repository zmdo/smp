"""console accounts

Revision ID: 003
Revises: 002
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "accounts" not in set(inspector.get_table_names()):
        op.create_table(
            "accounts",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("username", sa.String(64), nullable=False),
            sa.Column("password_hash", sa.String(128), nullable=False),
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("totp_secret", sa.String(64)),
            sa.Column("totp_pending_secret", sa.String(64)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("username", name="uq_accounts_username"),
        )
    if bind.dialect.name == "postgresql":
        op.execute("GRANT SELECT, INSERT, UPDATE ON accounts TO web_api")


def downgrade() -> None:
    op.drop_table("accounts")
