"""grant web_api access to tables created without privileges

Revision ID: 012
Revises: 011
Create Date: 2026-10-16
"""

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON exchange_accounts TO web_api")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON server_groups TO web_api")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON exchange_accounts FROM web_api")
    op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON server_groups FROM web_api")
