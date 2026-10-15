from __future__ import annotations

import bcrypt
from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from smp_web.config import settings


class PasswordChecker:
    def __init__(self, password: str):
        self._hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        self.is_default = password == "changeme"

    def verify(self, password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), self._hash)
        except ValueError:
            return False


passwords = PasswordChecker(settings.admin_password)
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def require_user(request: Request) -> None:
    if request.session.get("user") != "admin":
        raise HTTPException(status_code=401, detail="未登录")


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
        "host_key_fingerprint": server.host_key_fingerprint,
        "docker_version": server.docker_version,
        "compose_version": server.compose_version,
        "reachability": server.reachability,
        "last_checked_at": server.last_checked_at,
        "container_count": container_count,
        "created_at": server.created_at,
    }

