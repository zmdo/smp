"""server groups

Revision ID: 010
Revises: 009
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "server_groups" not in tables:
        op.create_table(
            "server_groups",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("name", name="uq_server_groups_name"),
        )
    if "servers" in tables:
        columns = {column["name"] for column in inspector.get_columns("servers")}
        if "group_id" not in columns:
            op.add_column("servers", sa.Column("group_id", sa.Uuid(as_uuid=True), nullable=True))
            op.create_index("ix_servers_group_id", "servers", ["group_id"])
            op.create_foreign_key(
                "fk_servers_group_id",
                "servers",
                "server_groups",
                ["group_id"],
                ["id"],
                ondelete="SET NULL",
            )
    if bind.dialect.name == "postgresql":
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON server_groups TO web_api")
