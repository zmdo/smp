"""SSH to a strategy server and run the fixed Docker commands."""

from __future__ import annotations

import base64
import hashlib
import io
import socket
from dataclasses import dataclass

import paramiko

from smp_ops.docker_parse import (
    ParseError,
    ParsedContainer,
    docker_access_message,
    parse_compose_version,
    parse_docker_version,
    parse_ps,
)

DOCKER_VERSION = "docker version --format '{{json .}}'"
COMPOSE_VERSION = "docker compose version --format json"
DOCKER_PS = "docker ps -a --no-trunc --format '{{json .}}'"


class OpsSSHError(Exception):
    def __init__(self, message: str, fingerprint: str | None = None):
        super().__init__(message)
        self.fingerprint = fingerprint


class FingerprintMismatch(OpsSSHError):
    def __init__(self, actual: str):
        super().__init__(f"主机密钥指纹不符，连接已拒绝。当前指纹是 {actual}", actual)


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ProbeResult:
    fingerprint: str
    docker_version: str
    compose_version: str
    output: str


@dataclass(frozen=True)
class InspectResult:
    fingerprint: str
    containers: list[ParsedContainer]
    output: str
    docker_version: str
    compose_version: str


def fingerprint_of(key: paramiko.PKey) -> str:
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def load_private_key(secret: str) -> paramiko.PKey:
    normalized = secret.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    try:
        return paramiko.PKey.from_private_key(io.StringIO(normalized))
    except paramiko.PasswordRequiredException as exc:
        raise OpsSSHError("私钥带有口令。请先去掉口令，再保存到控制台。") from exc
    except paramiko.SSHException as exc:
        raise OpsSSHError("私钥无法解析，请确认粘贴的是完整的私钥文件。") from exc


class _PinPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(self, expected: str | None):
        self.expected = expected
        self.seen: str | None = None

    def missing_host_key(self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey) -> None:
        seen = fingerprint_of(key)
        self.seen = seen
        if self.expected and seen != self.expected:
            raise FingerprintMismatch(seen)
        client.get_host_keys().add(hostname, key.get_name(), key)


def connect(
    *,
    host: str,
    port: int,
    username: str,
    auth_method: str,
    secret: str,
    expected_fingerprint: str | None,
) -> tuple[paramiko.SSHClient, _PinPolicy]:
    policy = _PinPolicy(expected_fingerprint)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(policy)
    kwargs: dict = {
        "hostname": host,
        "port": port,
        "username": username,
        "timeout": 8,
        "banner_timeout": 8,
        "auth_timeout": 8,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if auth_method == "password":
        kwargs["password"] = secret
    elif auth_method == "private_key":
        kwargs["pkey"] = load_private_key(secret)
    else:
        raise OpsSSHError("不支持的认证方式")
    try:
        client.connect(**kwargs)
    except FingerprintMismatch:
        client.close()
        raise
    except paramiko.AuthenticationException as exc:
        client.close()
        raise OpsSSHError("SSH 认证失败，请检查用户名、私钥或口令。", policy.seen) from exc
    except (socket.timeout, TimeoutError) as exc:
        client.close()
        raise OpsSSHError("连接超时。确认地址、端口，以及控制机能访问这台机器。", policy.seen) from exc
    except ConnectionRefusedError as exc:
        client.close()
        raise OpsSSHError("连接被拒绝。确认这台机器的 SSH 已启动，端口填写正确。", policy.seen) from exc
    except (paramiko.SSHException, OSError) as exc:
        client.close()
        raise OpsSSHError(f"无法连接 SSH：{exc}", policy.seen) from exc
    return client, policy


def run_command(client: paramiko.SSHClient, command: str, timeout: int = 15) -> CommandResult:
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return CommandResult(code=code, stdout=out, stderr=err)


def probe(client: paramiko.SSHClient, fingerprint: str) -> ProbeResult:
    docker_version, compose_version = read_versions(client, fingerprint)
    output = f"已连接。Docker {docker_version}，Compose {compose_version}。主机指纹 {fingerprint}。"
    return ProbeResult(
        fingerprint=fingerprint,
        docker_version=docker_version,
        compose_version=compose_version,
        output=output,
    )


def inspect_containers(client: paramiko.SSHClient, fingerprint: str) -> InspectResult:
    docker_version, compose_version = read_versions(client, fingerprint)
    listed = run_command(client, DOCKER_PS)
    if listed.code != 0:
        message = docker_access_message(listed.stderr) or _failure("docker ps", listed)
        raise OpsSSHError(message, fingerprint)
    try:
        containers = parse_ps(listed.stdout)
    except ParseError as exc:
        raise OpsSSHError(str(exc), fingerprint) from exc
    return InspectResult(
        fingerprint=fingerprint,
        containers=containers,
        output=f"已刷新，共 {len(containers)} 个容器。",
        docker_version=docker_version,
        compose_version=compose_version,
    )


def read_versions(client: paramiko.SSHClient, fingerprint: str) -> tuple[str, str]:
    docker = run_command(client, DOCKER_VERSION)
    if docker.code != 0:
        message = docker_access_message(docker.stderr) or _failure("Docker", docker)
        raise OpsSSHError(message, fingerprint)
    compose = run_command(client, COMPOSE_VERSION)
    if compose.code != 0:
        message = docker_access_message(compose.stderr) or _failure("Docker Compose", compose)
        raise OpsSSHError(message, fingerprint)
    try:
        return parse_docker_version(docker.stdout), parse_compose_version(compose.stdout)
    except ParseError as exc:
        raise OpsSSHError(str(exc), fingerprint) from exc


def _failure(what: str, result: CommandResult) -> str:
    detail = (result.stderr or result.stdout).strip()
    if not detail:
        return f"{what} 命令失败，退出码 {result.code}。"
    return f"{what} 命令失败：{detail}"
