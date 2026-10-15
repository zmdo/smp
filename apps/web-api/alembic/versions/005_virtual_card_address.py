"""virtual card billing address and platform

Revision ID: 005
Revises: 004
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

_COLUMNS = {
    "platform": sa.String(80),
    "country": sa.String(80),
    "region": sa.String(80),
    "city": sa.String(80),
    "address1": sa.String(160),
    "address2": sa.String(160),
    "postal_code": sa.String(20),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "virtual_cards" not in set(inspector.get_table_names()):
        return
    present = {column["name"] for column in inspector.get_columns("virtual_cards")}
    for name, column_type in _COLUMNS.items():
        if name not in present:
            op.add_column(
                "virtual_cards",
                sa.Column(name, column_type, nullable=False, server_default=""),
            )


def downgrade() -> None:
    for name in reversed(tuple(_COLUMNS)):
        op.drop_column("virtual_cards", name)
