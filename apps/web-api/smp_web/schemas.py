from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    password: str = Field(min_length=1)


class MeOut(BaseModel):
    authenticated: bool
    password_is_default: bool


class ServerIn(BaseModel):
    name: str
    intranet_host: str
    ssh_port: int = 22
    ssh_user: str
    auth_method: Literal["private_key", "password"]
    secret: str = Field(min_length=1)


class ServerUpdate(BaseModel):
    name: str | None = None
    intranet_host: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    auth_method: Literal["private_key", "password"] | None = None
    secret: str | None = None


class ServerOut(BaseModel):
    id: uuid.UUID
    name: str
    intranet_host: str
    ssh_port: int
    ssh_user: str
    auth_method: Literal["private_key", "password"]
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
