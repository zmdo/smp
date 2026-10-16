"""wallets

Revision ID: 006
Revises: 005
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("mnemonic_sha256", sa.String(64), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mnemonic_sha256", name="uq_wallets_mnemonic_sha256"),
        sa.CheckConstraint("word_count IN (12, 24)", name="ck_wallets_word_count"),
    )
    op.create_table(
        "wallet_accounts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", sa.Uuid(as_uuid=True), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("derivation_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("wallet_id", "derivation_index", name="uq_wallet_accounts_index"),
    )
    op.create_index("ix_wallet_accounts_wallet_id", "wallet_accounts", ["wallet_id"])
    op.create_table(
        "wallet_addresses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", sa.Uuid(as_uuid=True), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), sa.ForeignKey("wallet_accounts.id", ondelete="CASCADE")),
        sa.Column("chain", sa.String(32), nullable=False),
        sa.Column("address", sa.String(128), nullable=False),
        sa.Column("derivation_path", sa.String(80)),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("label", sa.String(80), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("wallet_id", "chain", "address", name="uq_wallet_addresses_chain"),
        sa.CheckConstraint("source IN ('derived', 'manual')", name="ck_wallet_addresses_source"),
    )
    op.create_index("ix_wallet_addresses_wallet_id", "wallet_addresses", ["wallet_id"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON wallets TO web_api")
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON wallet_accounts TO web_api")
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON wallet_addresses TO web_api")


def downgrade() -> None:
    op.drop_index("ix_wallet_addresses_wallet_id", table_name="wallet_addresses")
    op.drop_table("wallet_addresses")
    op.drop_index("ix_wallet_accounts_wallet_id", table_name="wallet_accounts")
    op.drop_table("wallet_accounts")
    op.drop_table("wallets")
