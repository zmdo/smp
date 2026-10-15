"""Field checks shared by the server form."""

from __future__ import annotations

import ipaddress
import re

_HOST = re.compile(r"[A-Za-z0-9._:-]{1,255}\Z")
_USER = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")


class FieldError(ValueError):
    pass


def clean_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 80:
        raise FieldError("名称需要 1 到 80 个字符")
    return cleaned


def clean_host(value: str) -> str:
    """Accept a public or private address: IPv4, IPv6, or a hostname."""
    cleaned = value.strip().rstrip(".")
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    if not cleaned or len(cleaned) > 255 or any(char.isspace() for char in cleaned):
        raise FieldError("地址格式不正确")
    try:
        return str(ipaddress.ip_address(cleaned))
    except ValueError:
        pass
    try:
        encoded = cleaned.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise FieldError("地址格式不正确") from exc
    if _HOST.fullmatch(cleaned) is None and _HOST.fullmatch(encoded) is None:
        raise FieldError("地址格式不正确")
    return cleaned


def clean_user(value: str) -> str:
    cleaned = value.strip()
    if _USER.fullmatch(cleaned) is None:
        raise FieldError("SSH 用户名只能包含字母、数字、点、下划线和连字符")
    return cleaned


def clean_port(value: int) -> int:
    if value < 1 or value > 65535:
        raise FieldError("SSH 端口需要在 1 到 65535 之间")
    return value
