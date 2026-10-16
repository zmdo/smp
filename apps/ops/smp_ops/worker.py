"""Claim ops jobs and apply SSH results."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from smp_ops.components import detect_components, install_missing
from smp_ops.crypto import decrypt
from smp_ops.docker_parse import excerpt, scrub
from smp_ops.ssh import (
    FingerprintMismatch,
    InspectResult,
    OpsSSHError,
    ProbeResult,
    connect,
    inspect_containers,
    probe,
)
from smpcore.components import load_catalog
from smpcore.models import OpsJob, Server, ServerContainer, SshKey

log = logging.getLogger("smp.ops")

_STALE_AFTER = timedelta(minutes=3)
_INSTALL_STALE_AFTER = timedelta(minutes=20)
_claim_lock = threading.Lock()


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    kwargs: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 5
    engine = create_engine(database_url, **kwargs)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def worker_loop(stop: threading.Event, sessions: sessionmaker[Session], fernet: Fernet) -> None:
    while not stop.is_set():
        job_id = claim_job(sessions)
        if job_id is None:
            stop.wait(0.5)
            continue
        try:
            execute_job(sessions, fernet, job_id)
        except Exception:
            log.exception("job %s failed inside the worker", job_id)
            mark_failed(sessions, job_id, "运维服务内部错误")


def schedule_loop(
    stop: threading.Event,
    sessions: sessionmaker[Session],
    interval_seconds: int,
) -> None:
    while not stop.is_set():
        try:
            recover_stale_jobs(sessions)
            enqueue_due_inspects(sessions, interval_seconds)
        except Exception:
            log.exception("scheduler tick failed")
        stop.wait(5)


def _ciphertext(session: Session, server: Server) -> str:
    if server.auth_method == "private_key" and server.ssh_key_id is not None:
        key = session.get(SshKey, server.ssh_key_id)
        if key is None:
            raise ValueError("登录密钥不存在")
        return key.secret_ciphertext
    return server.secret_ciphertext


def claim_job(sessions: sessionmaker[Session]) -> uuid.UUID | None:
    with _claim_lock, sessions() as session:
        running_servers = select(OpsJob.server_id).where(OpsJob.status == "running")
        statement = (
            select(OpsJob)
            .where(OpsJob.status == "queued")
            .where(OpsJob.server_id.not_in(running_servers))
            .order_by(OpsJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = session.execute(statement).scalar_one_or_none()
        if job is None:
            return None
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        session.commit()
        log.info("started job %s action=%s server=%s", job.id, job.action, job.server_id)
        return job.id


def execute_job(sessions: sessionmaker[Session], fernet: Fernet, job_id: uuid.UUID) -> None:
    with sessions() as session:
        job = session.get(OpsJob, job_id)
        if job is None or job.status != "running":
            return
        server = session.get(Server, job.server_id)
        if server is None:
            _finish(session, job, "failed", "服务器不存在")
            session.commit()
            return
        try:
            secret = decrypt(fernet, _ciphertext(session, server))
        except ValueError as exc:
            server.reachability = "offline"
            _finish(session, job, "failed", str(exc))
            session.commit()
            return
        action = job.action
        host = server.intranet_host
        port = server.ssh_port
        username = server.ssh_user
        auth_method = server.auth_method
        expected = server.host_key_fingerprint
        server_id = server.id
        auto_install = bool(server.auto_install)
        selected = _component_ids(server.install_component_ids)

    try:
        if action == "test_connection":
            _connect_and_prepare(
                sessions,
                job_id,
                server_id,
                secret,
                host,
                port,
                username,
                auth_method,
                expected,
                selected if auto_install else [],
            )
        elif action == "install_components":
            _connect_and_prepare(
                sessions,
                job_id,
                server_id,
                secret,
                host,
                port,
                username,
                auth_method,
                expected,
                [item.id for item in load_catalog()],
            )
        elif action == "inspect":
            result = _inspect(host, port, username, auth_method, secret, expected)
            _apply_inspect(sessions, job_id, server_id, secret, result)
        else:
            mark_failed(sessions, job_id, "该任务类型还没有实现")
    except FingerprintMismatch as exc:
        _apply_failure(sessions, job_id, server_id, secret, exc, pin_new_fingerprint=False, docker_down=False)
    except OpsSSHError as exc:
        docker_down = _is_docker_problem(str(exc))
        _apply_failure(sessions, job_id, server_id, secret, exc, pin_new_fingerprint=True, docker_down=docker_down)


def recover_stale_jobs(sessions: sessionmaker[Session]) -> None:
    with sessions() as session:
        stale = session.scalars(select(OpsJob).where(OpsJob.status == "running")).all()
        now = datetime.now(timezone.utc)
        for job in stale:
            if job.started_at is None:
                continue
            limit = _INSTALL_STALE_AFTER if job.action in {"install_components", "test_connection"} else _STALE_AFTER
            if job.started_at >= now - limit:
                continue
            job.status = "failed"
            job.finished_at = now
            job.output_excerpt = "运维服务中断，任务已失败，请重新执行。"
            log.warning("marked stale job %s as failed", job.id)
        session.commit()


def enqueue_due_inspects(sessions: sessionmaker[Session], interval_seconds: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=interval_seconds)
    with sessions() as session:
        servers = session.scalars(select(Server).where(Server.reachability == "online")).all()
        for server in servers:
            if server.last_checked_at is not None and server.last_checked_at > cutoff:
                continue
            active = session.scalar(
                select(OpsJob.id).where(
                    OpsJob.server_id == server.id,
                    OpsJob.action == "inspect",
                    OpsJob.status.in_(("queued", "running")),
                )
            )
            if active is not None:
                continue
            session.add(OpsJob(server_id=server.id, action="inspect", status="queued", output_excerpt=""))
        session.commit()


def mark_failed(sessions: sessionmaker[Session], job_id: uuid.UUID, message: str) -> None:
    with sessions() as session:
        job = session.get(OpsJob, job_id)
        if job is None or job.status in {"succeeded", "failed"}:
            return
        _finish(session, job, "failed", message)
        session.commit()


def _component_ids(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _save_component_status(sessions: sessionmaker[Session], server_id: uuid.UUID, status: dict) -> None:
    with sessions() as session:
        server = session.get(Server, server_id)
        if server is None:
            return
        server.component_status = json.dumps(status, ensure_ascii=False)
        session.commit()


def _open_client(
    host: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    expected: str | None,
):
    client, policy = connect(
        host=host,
        port=port,
        username=username,
        auth_method=auth_method,
        secret=secret,
        expected_fingerprint=expected,
    )
    seen = policy.seen
    if not seen:
        client.close()
        raise OpsSSHError("没有读到主机密钥指纹")
    return client, seen


def _connect_and_prepare(
    sessions: sessionmaker[Session],
    job_id: uuid.UUID,
    server_id: uuid.UUID,
    secret: str,
    host: str,
    port: int,
    username: str,
    auth_method: str,
    expected: str | None,
    component_ids: list[str],
) -> None:
    client, fingerprint = _open_client(host, port, username, auth_method, secret, expected)
    status: dict = {}
    try:
        status = detect_components(client)
        _save_component_status(sessions, server_id, status)
        report = install_missing(client, component_ids) if component_ids else None
        if report is not None and report.changed:
            client.close()
            client, fingerprint = _open_client(host, port, username, auth_method, secret, fingerprint)
        if report is not None:
            status = detect_components(client)
            _save_component_status(sessions, server_id, status)
        result = probe(client, fingerprint)
        if report is not None and report.notes:
            result = replace(result, output=" ".join(report.notes) + " " + result.output)
        _apply_probe(sessions, job_id, server_id, secret, result)
    except OpsSSHError:
        try:
            if client.get_transport() is not None and client.get_transport().is_active():
                status = detect_components(client)
                _save_component_status(sessions, server_id, status)
        except Exception:
            log.warning("component status refresh failed for %s", server_id)
        raise
    finally:
        client.close()


def _inspect(
    host: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    expected: str | None,
) -> InspectResult:
    client, policy = connect(
        host=host,
        port=port,
        username=username,
        auth_method=auth_method,
        secret=secret,
        expected_fingerprint=expected,
    )
    try:
        seen = policy.seen
        if not seen:
            raise OpsSSHError("没有读到主机密钥指纹")
        return inspect_containers(client, seen)
    finally:
        client.close()


def _apply_probe(
    sessions: sessionmaker[Session],
    job_id: uuid.UUID,
    server_id: uuid.UUID,
    secret: str,
    result: ProbeResult,
) -> None:
    now = datetime.now(timezone.utc)
    with sessions() as session:
        server = session.get(Server, server_id)
        job = session.get(OpsJob, job_id)
        if server is None or job is None:
            return
        server.host_key_fingerprint = result.fingerprint
        server.docker_version = result.docker_version
        server.compose_version = result.compose_version
        server.reachability = "online"
        server.last_checked_at = now
        _finish(session, job, "succeeded", scrub(result.output, secret))
        _queue_inspect(session, server_id)
        session.commit()


def _queue_inspect(session: Session, server_id: uuid.UUID) -> None:
    active = session.scalar(
        select(OpsJob.id).where(
            OpsJob.server_id == server_id,
            OpsJob.action == "inspect",
            OpsJob.status.in_(("queued", "running")),
        )
    )
    if active is None:
        session.add(OpsJob(server_id=server_id, action="inspect", status="queued", output_excerpt=""))


def _apply_inspect(
    sessions: sessionmaker[Session],
    job_id: uuid.UUID,
    server_id: uuid.UUID,
    secret: str,
    result: InspectResult,
) -> None:
    now = datetime.now(timezone.utc)
    with sessions() as session:
        server = session.get(Server, server_id)
        job = session.get(OpsJob, job_id)
        if server is None or job is None:
            return
        if server.host_key_fingerprint is None:
            server.host_key_fingerprint = result.fingerprint
        server.docker_version = result.docker_version
        server.compose_version = result.compose_version
        server.reachability = "online"
        server.last_checked_at = now
        session.execute(delete(ServerContainer).where(ServerContainer.server_id == server_id))
        for item in result.containers:
            session.add(
                ServerContainer(
                    server_id=server_id,
                    container_id=item.container_id,
                    name=item.name,
                    image=item.image,
                    status=item.status,
                    ports=item.ports,
                    managed=item.managed,
                    strategy_slug=item.strategy_slug,
                    observed_at=now,
                )
            )
        _finish(session, job, "succeeded", scrub(result.output, secret))
        session.commit()


def _apply_failure(
    sessions: sessionmaker[Session],
    job_id: uuid.UUID,
    server_id: uuid.UUID,
    secret: str,
    exc: OpsSSHError,
    *,
    pin_new_fingerprint: bool,
    docker_down: bool,
) -> None:
    now = datetime.now(timezone.utc)
    with sessions() as session:
        server = session.get(Server, server_id)
        job = session.get(OpsJob, job_id)
        if server is None or job is None:
            return
        if pin_new_fingerprint and exc.fingerprint and server.host_key_fingerprint is None:
            server.host_key_fingerprint = exc.fingerprint
        server.reachability = "docker_unavailable" if docker_down else "offline"
        server.last_checked_at = now
        if docker_down:
            server.docker_version = None
            server.compose_version = None
        _finish(session, job, "failed", scrub(str(exc), secret))
        session.commit()


def _finish(session: Session, job: OpsJob, status: str, message: str) -> None:
    job.status = status
    job.finished_at = datetime.now(timezone.utc)
    job.output_excerpt = excerpt(message)


def _is_docker_problem(message: str) -> bool:
    markers = ("Docker", "Compose", "docker")
    return any(marker in message for marker in markers)
