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


class ServerUpdate(BaseModel):
    name: str | None = None
    intranet_host: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    auth_method: Literal["private_key", "password"] | None = None
    secret: str | None = None
    ssh_key_id: uuid.UUID | None = None
    ssh_key_name: str | None = None


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
