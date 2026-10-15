"""Parse Docker CLI output. These functions do not open a connection."""

from __future__ import annotations

import json
from dataclasses import dataclass


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedContainer:
    container_id: str
    name: str
    image: str
    status: str
    ports: str
    managed: bool
    strategy_slug: str | None


def excerpt(text: str, limit: int = 8000) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return "…\n" + cleaned[-limit:]


def scrub(text: str, secret: str) -> str:
    if secret and len(secret) >= 4 and secret in text:
        return text.replace(secret, "***")
    return text


def parse_labels(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for part in raw.split(","):
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        labels[key.strip()] = value.strip()
    return labels


def parse_ps(output: str) -> list[ParsedContainer]:
    rows: list[ParsedContainer] = []
    for line_number, line in enumerate(output.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ParseError(f"第 {line_number} 行不是 JSON：{exc}") from exc
        if not isinstance(payload, dict):
            raise ParseError(f"第 {line_number} 行不是容器记录")
        rows.append(_container_from_payload(payload))
    return rows


def parse_docker_version(output: str) -> str:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ParseError(f"无法解析 Docker 版本：{exc}") from exc
    if not isinstance(payload, dict):
        raise ParseError("无法解析 Docker 版本")
    server = payload.get("Server") if isinstance(payload.get("Server"), dict) else {}
    client = payload.get("Client") if isinstance(payload.get("Client"), dict) else {}
    version = server.get("Version") or client.get("Version")
    if not version:
        raise ParseError("Docker 版本输出里没有 Version")
    return str(version)[:64]


def parse_compose_version(output: str) -> str:
    text = output.strip()
    if not text:
        raise ParseError("没有读到 Docker Compose 版本")
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParseError(f"无法解析 Compose 版本：{exc}") from exc
        if not isinstance(payload, dict):
            raise ParseError("无法解析 Compose 版本")
        version = payload.get("version") or payload.get("short")
        if not version:
            raise ParseError("Compose 版本输出里没有 version")
        return str(version)[:64]
    token = text.split()[-1]
    return token[:64]


def docker_access_message(stderr: str) -> str | None:
    lowered = stderr.lower()
    if "permission denied" in lowered and "docker" in lowered:
        return "SSH 用户不能访问 Docker。把该用户加入 docker 组后重新测试连接。"
    if "command not found" in lowered and "docker" in lowered:
        return "这台机器上没有 docker 命令。需要先安装 Docker Engine 和 Compose 插件。"
    return None


def _container_from_payload(payload: dict) -> ParsedContainer:
    container_id = str(payload.get("ID") or "").strip()
    if not container_id:
        raise ParseError("容器记录缺少 ID")
    raw_name = str(payload.get("Names") or "").split(",")[0].strip()
    name = raw_name.lstrip("/") or container_id[:12]
    labels = parse_labels(str(payload.get("Labels") or ""))
    managed_value = labels.get("smp.managed", "").lower()
    managed = managed_value in {"true", "1", "yes"}
    slug = labels.get("smp.strategy") or None
    state = str(payload.get("State") or payload.get("Status") or "unknown").strip()
    return ParsedContainer(
        container_id=container_id[:80],
        name=name[:255],
        image=str(payload.get("Image") or "")[:512],
        status=state[:64] or "unknown",
        ports=str(payload.get("Ports") or "")[:4000],
        managed=managed,
        strategy_slug=slug[:80] if slug else None,
    )
