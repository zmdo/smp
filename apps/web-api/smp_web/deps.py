from __future__ import annotations

import json

from fastapi import HTTPException, Request
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from smp_web.config import settings
from smpcore.models import Account

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def require_user(request: Request) -> str:
    username = request.session.get("user")
    if not isinstance(username, str) or not username:
        raise HTTPException(status_code=401, detail="未登录")
    with SessionLocal() as session:
        exists = session.scalar(select(Account.id).where(Account.username == username))
    if exists is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="未登录")
    return username


def job_out(job) -> dict:
    return {
        "id": job.id,
        "server_id": job.server_id,
        "action": job.action,
        "status": job.status,
        "output_excerpt": job.output_excerpt,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


def server_out(server, container_count: int | None) -> dict:
    return {
        "id": server.id,
        "name": server.name,
        "intranet_host": server.intranet_host,
        "ssh_port": server.ssh_port,
        "ssh_user": server.ssh_user,
        "auth_method": server.auth_method,
        "ssh_key_id": server.ssh_key_id,
        "ssh_key_name": server.ssh_key.name if server.ssh_key is not None else None,
        "host_key_fingerprint": server.host_key_fingerprint,
        "docker_version": server.docker_version,
        "compose_version": server.compose_version,
        "reachability": server.reachability,
        "last_checked_at": server.last_checked_at,
        "cpu_cores": server.cpu_cores,
        "cpu_percent": server.cpu_percent,
        "mem_total_bytes": server.mem_total_bytes,
        "mem_used_bytes": server.mem_used_bytes,
        "disk_total_bytes": server.disk_total_bytes,
        "disk_used_bytes": server.disk_used_bytes,
        "metrics_at": server.metrics_at,
        "region": server.region,
        "group_id": server.group_id,
        "group_name": server.group.name if server.group is not None else None,
        "auto_install": bool(server.auto_install),
        "component_ids": _json_list(server.install_component_ids),
        "component_status": _json_status(server.component_status),
        "container_count": container_count,
        "created_at": server.created_at,
    }


def _json_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _json_status(raw: str | None) -> dict[str, dict[str, object]]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    status: dict[str, dict[str, object]] = {}
    for key, item in value.items():
        if not isinstance(item, dict):
            continue
        status[str(key)] = {
            "installed": bool(item.get("installed")),
            "detail": str(item.get("detail") or ""),
        }
    return status

