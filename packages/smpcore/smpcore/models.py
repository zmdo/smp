"""Tables shared by the website and the ops worker."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SshKey(Base):
    __tablename__ = "ssh_keys"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_ssh_keys_fingerprint"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    servers: Mapped[list[Server]] = relationship(back_populates="ssh_key")


class Server(Base):
    __tablename__ = "servers"
    __table_args__ = (
        UniqueConstraint("intranet_host", "ssh_port", name="uq_servers_host_port"),
        CheckConstraint(
            "auth_method IN ('private_key', 'password')",
            name="ck_servers_auth_method",
        ),
        CheckConstraint(
            "reachability IN ('online', 'offline', 'docker_unavailable', 'unknown')",
            name="ck_servers_reachability",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    intranet_host: Mapped[str] = mapped_column(String(255), nullable=False)
    ssh_port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    ssh_user: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_method: Mapped[str] = mapped_column(String(32), nullable=False)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    ssh_key_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ssh_keys.id", ondelete="RESTRICT"), index=True
    )
    host_key_fingerprint: Mapped[str | None] = mapped_column(String(128))
    docker_version: Mapped[str | None] = mapped_column(String(64))
    compose_version: Mapped[str | None] = mapped_column(String(64))
    reachability: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow
    )

    containers: Mapped[list[ServerContainer]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    ssh_key: Mapped[SshKey | None] = relationship(back_populates="servers")
    jobs: Mapped[list[OpsJob]] = relationship(back_populates="server", cascade="all, delete-orphan")


class ServerContainer(Base):
    __tablename__ = "server_containers"
    __table_args__ = (
        UniqueConstraint("server_id", "container_id", name="uq_server_container"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    container_id: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    ports: Mapped[str] = mapped_column(Text, nullable=False, default="")
    managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strategy_slug: Mapped[str | None] = mapped_column(String(80))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    server: Mapped[Server] = relationship(back_populates="containers")


class OpsJob(Base):
    __tablename__ = "ops_jobs"
    __table_args__ = (
        CheckConstraint(
            "action IN ('test_connection', 'inspect', 'deploy', 'start', 'stop', 'restart', 'logs')",
            name="ck_ops_jobs_action",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_ops_jobs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    output_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    server: Mapped[Server] = relationship(back_populates="jobs")


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("username", name="uq_accounts_username"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_pending_secret: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
