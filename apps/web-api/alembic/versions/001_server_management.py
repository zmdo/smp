"""server management tables

Revision ID: 001
Revises:
Create Date: 2026-10-15
"""

from alembic import op

from smpcore.models import Base

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

GRANTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON servers TO web_api",
    "GRANT SELECT, INSERT ON ops_jobs TO web_api",
    "GRANT SELECT, DELETE ON server_containers TO web_api",
    "GRANT SELECT, UPDATE ON servers TO ops",
    "GRANT SELECT, INSERT, UPDATE ON ops_jobs TO ops",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON server_containers TO ops",
)


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    for statement in GRANTS:
        op.execute(statement)


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
