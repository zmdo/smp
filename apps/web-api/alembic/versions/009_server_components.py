"""server region, optional component install, and the install job

Revision ID: 009
Revises: 008
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

_ACTIONS = (
    "'test_connection', 'inspect', 'deploy', 'start', 'stop', 'restart', 'logs', 'install_components'"
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "servers" in set(inspector.get_table_names()):
        present = {column["name"] for column in inspector.get_columns("servers")}
        if "region" not in present:
            op.add_column("servers", sa.Column("region", sa.String(80), nullable=True))
        if "auto_install" not in present:
            op.add_column(
                "servers",
                sa.Column("auto_install", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if "install_component_ids" not in present:
            op.add_column(
                "servers",
                sa.Column("install_component_ids", sa.Text(), nullable=False, server_default="[]"),
            )
        if "component_status" not in present:
            op.add_column(
                "servers",
                sa.Column("component_status", sa.Text(), nullable=False, server_default="{}"),
            )
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE ops_jobs DROP CONSTRAINT IF EXISTS ck_ops_jobs_action")
        op.execute(
            "ALTER TABLE ops_jobs ADD CONSTRAINT ck_ops_jobs_action "
            f"CHECK (action IN ({_ACTIONS}))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE ops_jobs DROP CONSTRAINT IF EXISTS ck_ops_jobs_action")
        op.execute(
            "ALTER TABLE ops_jobs ADD CONSTRAINT ck_ops_jobs_action "
            "CHECK (action IN ('test_connection', 'inspect', 'deploy', 'start', 'stop', 'restart', 'logs'))"
        )
    for name in ("component_status", "install_component_ids", "auto_install", "region"):
        op.drop_column("servers", name)
