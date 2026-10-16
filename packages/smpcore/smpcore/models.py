"""Tables shared by the website and the ops worker."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    BigInteger,
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


class ServerGroup(Base):
    __tablename__ = "server_groups"
    __table_args__ = (UniqueConstraint("name", name="uq_server_groups_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    servers: Mapped[list[Server]] = relationship(back_populates="group")


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
    cpu_cores: Mapped[int | None] = mapped_column(Integer)
    cpu_percent: Mapped[int | None] = mapped_column(Integer)
    mem_total_bytes: Mapped[int | None] = mapped_column(BigInteger)
    mem_used_bytes: Mapped[int | None] = mapped_column(BigInteger)
    disk_total_bytes: Mapped[int | None] = mapped_column(BigInteger)
    disk_used_bytes: Mapped[int | None] = mapped_column(BigInteger)
    metrics_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    region: Mapped[str | None] = mapped_column(String(80))
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("server_groups.id", ondelete="SET NULL"), index=True
    )
    auto_install: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    install_component_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    component_status: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
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
    group: Mapped[ServerGroup | None] = relationship(back_populates="servers")
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
            "action IN ('test_connection', 'inspect', 'deploy', 'start', 'stop', 'restart', 'logs', 'install_components')",
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


class VirtualCard(Base):
    __tablename__ = "virtual_cards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    platform: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    holder: Mapped[str] = mapped_column(String(80), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    region: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    address1: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    address2: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    expiry: Mapped[str] = mapped_column(String(5), nullable=False)
    last4: Mapped[str] = mapped_column(String(4), nullable=False)
    number_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    cvv_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("mnemonic_sha256", name="uq_wallets_mnemonic_sha256"),
        CheckConstraint("word_count IN (12, 24)", name="ck_wallets_word_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    mnemonic_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    accounts: Mapped[list[WalletAccount]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan"
    )


class WalletAccount(Base):
    __tablename__ = "wallet_accounts"
    __table_args__ = (UniqueConstraint("wallet_id", "derivation_index", name="uq_wallet_accounts_index"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    derivation_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    wallet: Mapped[Wallet] = relationship(back_populates="accounts")
    addresses: Mapped[list[WalletAddress]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class WalletAddress(Base):
    __tablename__ = "wallet_addresses"
    __table_args__ = (
        UniqueConstraint("wallet_id", "chain", "address", name="uq_wallet_addresses_chain"),
        CheckConstraint("source IN ('derived', 'manual')", name="ck_wallet_addresses_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("wallet_accounts.id", ondelete="CASCADE")
    )
    chain: Mapped[str] = mapped_column(String(32), nullable=False)
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    derivation_path: Mapped[str | None] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    account: Mapped[WalletAccount | None] = relationship(back_populates="addresses")


class ExchangeAccount(Base):
    __tablename__ = "exchange_accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    venue: Mapped[str] = mapped_column(String(32), nullable=False)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    balances: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    balance_error: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


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


class McpSettings(Base):
    """Single row (id = 1) that controls the console's own MCP endpoint."""

    __tablename__ = "mcp_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_hash: Mapped[str | None] = mapped_column(String(64))
    token_last4: Mapped[str | None] = mapped_column(String(8))
    expose_servers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expose_wallets: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expose_cards: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
