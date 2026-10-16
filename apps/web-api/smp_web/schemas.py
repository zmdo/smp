from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)
    totp_code: str | None = None


class LoginOut(BaseModel):
    ok: bool
    totp_required: bool = False


class MeOut(BaseModel):
    authenticated: bool
    username: str | None = None
    password_is_default: bool
    totp_enabled: bool = False


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class TotpCodeIn(BaseModel):
    code: str = Field(min_length=1)


class TotpDisableIn(BaseModel):
    password: str = Field(min_length=1)
    code: str = Field(min_length=1)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1, max_length=72)


class UsernameChangeIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class VirtualCardIn(BaseModel):
    name: str
    platform: str
    holder: str
    number: str
    expiry: str
    cvv: str
    country: str
    region: str
    city: str
    address1: str
    address2: str = ""
    postal_code: str
    note: str = ""


class VirtualCardOut(BaseModel):
    id: uuid.UUID
    name: str
    platform: str
    holder: str
    expiry: str
    last4: str
    country: str
    region: str
    city: str
    address1: str
    address2: str
    postal_code: str
    note: str
    created_at: datetime


class VirtualCardSecretOut(BaseModel):
    number: str
    cvv: str


class SshKeyIn(BaseModel):
    name: str
    secret: str = Field(min_length=1)


class SshKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    fingerprint: str
    server_count: int
    created_at: datetime


class ServerIn(BaseModel):
    name: str
    intranet_host: str
    ssh_port: int = 22
    ssh_user: str
    auth_method: Literal["private_key", "password"]
    secret: str | None = None
    ssh_key_id: uuid.UUID | None = None
    ssh_key_name: str | None = None
    auto_install: bool = False
    component_ids: list[str] = Field(default_factory=list)


class ServerUpdate(BaseModel):
    name: str | None = None
    intranet_host: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    auth_method: Literal["private_key", "password"] | None = None
    secret: str | None = None
    ssh_key_id: uuid.UUID | None = None
    ssh_key_name: str | None = None
    auto_install: bool | None = None
    component_ids: list[str] | None = None


class ServerOut(BaseModel):
    id: uuid.UUID
    name: str
    intranet_host: str
    ssh_port: int
    ssh_user: str
    auth_method: Literal["private_key", "password"]
    ssh_key_id: uuid.UUID | None
    ssh_key_name: str | None
    host_key_fingerprint: str | None
    docker_version: str | None
    compose_version: str | None
    reachability: str
    last_checked_at: datetime | None
    cpu_cores: int | None = None
    cpu_percent: int | None = None
    mem_total_bytes: int | None = None
    mem_used_bytes: int | None = None
    disk_total_bytes: int | None = None
    disk_used_bytes: int | None = None
    metrics_at: datetime | None = None
    region: str | None = None
    auto_install: bool = False
    component_ids: list[str] = Field(default_factory=list)
    component_status: dict[str, dict] = Field(default_factory=dict)
    container_count: int | None
    created_at: datetime


class ContainerOut(BaseModel):
    container_id: str
    name: str
    image: str
    status: str
    ports: str
    managed: bool
    strategy_slug: str | None
    observed_at: datetime


class JobOut(BaseModel):
    id: uuid.UUID
    server_id: uuid.UUID
    action: str
    status: str
    output_excerpt: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ServerDetailOut(ServerOut):
    containers: list[ContainerOut]
    recent_jobs: list[JobOut]


class ServerCreatedOut(BaseModel):
    server: ServerOut
    job: JobOut | None = None


class WalletCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1)
    mnemonic: str | None = None


class WalletOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


class WalletAddressOut(BaseModel):
    chain: str
    chain_label: str
    address: str
    derivation_path: str | None
    source: Literal["derived", "manual"]


class WalletAccountOut(BaseModel):
    id: uuid.UUID
    name: str
    derivation_index: int
    addresses: list[WalletAddressOut]


class WalletDetailOut(WalletOut):
    accounts: list[WalletAccountOut]


class WalletCreatedOut(WalletOut):
    mnemonic: str | None = None


class McpSettingsOut(BaseModel):
    enabled: bool
    has_token: bool
    token_last4: str | None
    expose_servers: bool
    expose_wallets: bool
    expose_cards: bool


class McpSettingsIn(BaseModel):
    enabled: bool
    expose_servers: bool
    expose_wallets: bool
    expose_cards: bool


class McpTokenOut(BaseModel):
    token: str
    token_last4: str
