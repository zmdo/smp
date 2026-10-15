"""ssh key library

Revision ID: 002
Revises: 001
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "ssh_keys" not in tables:
        op.create_table(
            "ssh_keys",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("fingerprint", sa.String(128), nullable=False),
            sa.Column("secret_ciphertext", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("fingerprint", name="uq_ssh_keys_fingerprint"),
        )
    columns = {column["name"] for column in inspector.get_columns("servers")}
    if "ssh_key_id" not in columns:
        op.add_column("servers", sa.Column("ssh_key_id", sa.Uuid(as_uuid=True), nullable=True))
        op.create_index("ix_servers_ssh_key_id", "servers", ["ssh_key_id"])
        op.create_foreign_key(
            "fk_servers_ssh_key",
            "servers",
            "ssh_keys",
            ["ssh_key_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    if bind.dialect.name == "postgresql":
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ssh_keys TO web_api")
        op.execute("GRANT SELECT ON ssh_keys TO ops")


def downgrade() -> None:
    op.drop_constraint("fk_servers_ssh_key", "servers", type_="foreignkey")
    op.drop_index("ix_servers_ssh_key_id", table_name="servers")
    op.drop_column("servers", "ssh_key_id")
    op.drop_table("ssh_keys")
