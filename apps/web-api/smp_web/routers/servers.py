from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from smp_web.deps import get_session, job_out, require_user, server_out
from smp_web.key_store import require_key, store_private_key
from smp_web.schemas import JobOut, ServerCreatedOut, ServerDetailOut, ServerIn, ServerOut, ServerUpdate
from smp_web.secrets_client import encrypt_secret
from smp_web.validation import FieldError, clean_host, clean_name, clean_port, clean_user
from smpcore.models import OpsJob, Server, ServerContainer

router = APIRouter(prefix="/api/servers", dependencies=[Depends(require_user)])

_METRIC_COLUMNS = {
    "cpu_cores": "INTEGER",
    "cpu_percent": "INTEGER",
    "mem_total_bytes": "BIGINT",
    "mem_used_bytes": "BIGINT",
    "disk_total_bytes": "BIGINT",
    "disk_used_bytes": "BIGINT",
    "metrics_at": "DATETIME",
}


def ensure_server_metric_columns() -> None:
    from sqlalchemy import inspect, text

    from smp_web.deps import engine

    inspector = inspect(engine)
    if "servers" not in set(inspector.get_table_names()):
        return
    present = {column["name"] for column in inspector.get_columns("servers")}
    missing = [name for name in _METRIC_COLUMNS if name not in present]
    if not missing:
        return
    with engine.begin() as connection:
        for name in missing:
            connection.execute(text(f"ALTER TABLE servers ADD COLUMN {name} {_METRIC_COLUMNS[name]}"))


@router.get("", response_model=list[ServerOut])
@router.get("/", response_model=list[ServerOut], include_in_schema=False)
def list_servers(session: Session = Depends(get_session)) -> list[dict]:
    container_count = (
        select(func.count(ServerContainer.id))
        .where(ServerContainer.server_id == Server.id)
        .correlate(Server)
        .scalar_subquery()
    )
    inspected_at = (
        select(func.max(OpsJob.finished_at))
        .where(
            OpsJob.server_id == Server.id,
            OpsJob.action == "inspect",
            OpsJob.status == "succeeded",
        )
        .correlate(Server)
        .scalar_subquery()
    )
    rows = session.execute(
        select(Server, container_count, inspected_at).order_by(Server.created_at.desc())
    ).all()
    return [
        server_out(server, None if inspected is None else int(count or 0))
        for server, count, inspected in rows
    ]


@router.post("", response_model=ServerCreatedOut, status_code=201)
def create_server(body: ServerIn, session: Session = Depends(get_session)) -> dict:
    try:
        name = clean_name(body.name)
        host = clean_host(body.intranet_host)
        user = clean_user(body.ssh_user)
        port = clean_port(body.ssh_port)
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    server = Server(
        name=name,
        intranet_host=host,
        ssh_port=port,
        ssh_user=user,
        auth_method=body.auth_method,
        secret_ciphertext="",
        reachability="unknown",
    )
    session.add(server)
    _bind_auth(session, server, body, creating=True)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="该地址和 SSH 端口已经登记过") from exc
    job = _enqueue(session, server, "test_connection")
    session.commit()
    session.refresh(server)
    session.refresh(job)
    return {"server": server_out(server, None), "job": job_out(job)}


@router.get("/{server_id}", response_model=ServerDetailOut)
def get_server(server_id: str, session: Session = Depends(get_session)) -> dict:
    server = _get(session, server_id)
    inspected = _last_inspect(session, server.id)
    count = session.scalar(
        select(func.count(ServerContainer.id)).where(ServerContainer.server_id == server.id)
    )
    containers = session.scalars(
        select(ServerContainer)
        .where(ServerContainer.server_id == server.id)
        .order_by(ServerContainer.managed.desc(), ServerContainer.name)
    ).all()
    jobs = session.scalars(
        select(OpsJob).where(OpsJob.server_id == server.id).order_by(OpsJob.created_at.desc()).limit(10)
    ).all()
    payload = server_out(server, None if inspected is None else int(count or 0))
    payload["containers"] = [
        {
            "container_id": item.container_id,
            "name": item.name,
            "image": item.image,
            "status": item.status,
            "ports": item.ports,
            "managed": item.managed,
            "strategy_slug": item.strategy_slug,
            "observed_at": item.observed_at,
        }
        for item in containers
    ]
    payload["recent_jobs"] = [job_out(job) for job in jobs]
    return payload


@router.patch("/{server_id}", response_model=ServerCreatedOut)
def update_server(server_id: str, body: ServerUpdate, session: Session = Depends(get_session)) -> dict:
    server = _get(session, server_id)
    try:
        connection_changed = _apply_update(server, body)
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    connection_changed = _bind_auth(session, server, body, creating=False) or connection_changed
    if connection_changed:
        server.host_key_fingerprint = None
        server.reachability = "unknown"
        server.docker_version = None
        server.compose_version = None
        server.last_checked_at = None
        session.execute(delete(ServerContainer).where(ServerContainer.server_id == server.id))
    job = _enqueue(session, server, "test_connection") if connection_changed else None
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="该地址和 SSH 端口已经登记过") from exc
    session.refresh(server)
    if job is not None:
        session.refresh(job)
    return {"server": server_out(server, None), "job": job_out(job) if job else None}


@router.delete("/{server_id}", status_code=204)
def delete_server(server_id: str, session: Session = Depends(get_session)) -> Response:
    server = _get(session, server_id)
    session.execute(delete(Server).where(Server.id == server.id))
    session.commit()
    return Response(status_code=204)


@router.post("/{server_id}/test", response_model=JobOut)
def test_connection(server_id: str, session: Session = Depends(get_session)) -> dict:
    server = _get(session, server_id)
    job = _enqueue(session, server, "test_connection")
    session.commit()
    session.refresh(job)
    return job_out(job)


@router.post("/{server_id}/inspect", response_model=JobOut)
def inspect_server(server_id: str, session: Session = Depends(get_session)) -> dict:
    server = _get(session, server_id)
    job = _enqueue(session, server, "inspect")
    session.commit()
    session.refresh(job)
    return job_out(job)


@router.get("/{server_id}/containers")
def list_containers(server_id: str, session: Session = Depends(get_session)) -> dict:
    detail = get_server(server_id, session)
    return {"containers": detail["containers"], "container_count": detail["container_count"]}


def _bind_auth(session: Session, server: Server, body: ServerIn | ServerUpdate, *, creating: bool) -> bool:
    method = body.auth_method or server.auth_method
    if method == "private_key":
        if body.ssh_key_id is not None:
            key = require_key(session, body.ssh_key_id)
        elif body.secret and body.secret.strip():
            key = store_private_key(session, body.secret, body.ssh_key_name)
        elif creating or (body.auth_method == "private_key" and server.auth_method != "private_key"):
            raise HTTPException(status_code=422, detail="请选择或粘贴私钥")
        else:
            return False
        changed = server.ssh_key_id != key.id or server.auth_method != "private_key"
        server.auth_method = "private_key"
        server.ssh_key_id = key.id
        if not server.secret_ciphertext:
            server.secret_ciphertext = ""
        return changed
    if method != "password":
        raise HTTPException(status_code=422, detail="认证方式只能是私钥或口令")
    if body.secret:
        ciphertext, _fingerprint = encrypt_secret(body.secret, "password")
        server.secret_ciphertext = ciphertext
        server.auth_method = "password"
        server.ssh_key_id = None
        return True
    if creating or (body.auth_method == "password" and server.auth_method != "password"):
        raise HTTPException(status_code=422, detail="请填写口令")
    return False


def _apply_update(server: Server, body: ServerUpdate) -> bool:
    changed = False
    if body.name is not None:
        server.name = clean_name(body.name)
    if body.intranet_host is not None:
        host = clean_host(body.intranet_host)
        changed = changed or host != server.intranet_host
        server.intranet_host = host
    if body.ssh_port is not None:
        port = clean_port(body.ssh_port)
        changed = changed or port != server.ssh_port
        server.ssh_port = port
    if body.ssh_user is not None:
        user = clean_user(body.ssh_user)
        changed = changed or user != server.ssh_user
        server.ssh_user = user
    return changed


def _enqueue(session: Session, server: Server, action: str) -> OpsJob:
    existing = session.scalar(
        select(OpsJob).where(
            OpsJob.server_id == server.id,
            OpsJob.action == action,
            OpsJob.status.in_(("queued", "running")),
        )
    )
    if existing is not None:
        return existing
    job = OpsJob(server_id=server.id, action=action, status="queued", output_excerpt="")
    session.add(job)
    session.flush()
    return job


def _get(session: Session, server_id: str) -> Server:
    try:
        parsed = uuid.UUID(server_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="服务器不存在") from exc
    server = session.get(Server, parsed)
    if server is None:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


def _last_inspect(session: Session, server_id: uuid.UUID):
    return session.scalar(
        select(func.max(OpsJob.finished_at)).where(
            OpsJob.server_id == server_id,
            OpsJob.action == "inspect",
            OpsJob.status == "succeeded",
        )
    )
