"""Add columns the running SQLite database does not get from Alembic."""

from __future__ import annotations

import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_SERVER_COLUMNS = {
    "region": "VARCHAR(80)",
    "auto_install": "BOOLEAN NOT NULL DEFAULT 0",
    "install_component_ids": "TEXT NOT NULL DEFAULT '[]'",
    "component_status": "TEXT NOT NULL DEFAULT '{}'",
    "group_id": "CHAR(32)",
}


def ensure_runtime_schema(engine: Engine) -> None:
    from smpcore.models import ServerGroup

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "server_groups" not in tables:
            ServerGroup.__table__.create(connection)
        if "exchange_accounts" not in tables:
            from smpcore.models import ExchangeAccount

            ExchangeAccount.__table__.create(connection)
        if "servers" in tables:
            present = {column["name"] for column in inspector.get_columns("servers")}
            for name, column_type in _SERVER_COLUMNS.items():
                if name in present:
                    continue
                connection.execute(text(f"ALTER TABLE servers ADD COLUMN {name} {column_type}"))
    if engine.dialect.name == "sqlite" and "ops_jobs" in tables:
        _ensure_sqlite_job_action(engine)


def _ensure_sqlite_job_action(engine: Engine) -> None:
    with engine.connect() as connection:
        sql = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ops_jobs'")
        ).scalar()
        if not sql or "install_components" in sql:
            return
        updated = _extend_action_check(str(sql))
        indexes = connection.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'index' AND tbl_name = 'ops_jobs' AND sql IS NOT NULL"
            )
        ).scalars().all()
        connection.execute(text("ALTER TABLE ops_jobs RENAME TO ops_jobs_old"))
        connection.execute(text(updated))
        connection.execute(text("INSERT INTO ops_jobs SELECT * FROM ops_jobs_old"))
        connection.execute(text("DROP TABLE ops_jobs_old"))
        for index_sql in indexes:
            connection.execute(text(index_sql))
        connection.commit()


def _extend_action_check(sql: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        body = match.group(1)
        if "install_components" in body:
            return match.group(0)
        return f"CHECK (action IN ({body}, 'install_components'))"

    updated, count = re.subn(r"CHECK \(action IN \(([^)]*)\)\)", replacer, sql, count=1)
    if count != 1:
        raise RuntimeError("没有找到任务类型约束")
    return updated
