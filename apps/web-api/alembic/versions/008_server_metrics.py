"""server host metrics

Revision ID: 008
Revises: 007
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

_COLUMNS = {
    "cpu_cores": sa.Integer(),
    "cpu_percent": sa.Integer(),
    "mem_total_bytes": sa.BigInteger(),
    "mem_used_bytes": sa.BigInteger(),
    "disk_total_bytes": sa.BigInteger(),
    "disk_used_bytes": sa.BigInteger(),
    "metrics_at": sa.DateTime(timezone=True),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "servers" not in set(inspector.get_table_names()):
        return
    present = {column["name"] for column in inspector.get_columns("servers")}
    for name, column_type in _COLUMNS.items():
        if name not in present:
            op.add_column("servers", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    for name in reversed(list(_COLUMNS)):
        op.drop_column("servers", name)
