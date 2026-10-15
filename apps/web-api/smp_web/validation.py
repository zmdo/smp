"""Field checks shared by the server form."""

from __future__ import annotations

import ipaddress
import re

_HOST = re.compile(r"[A-Za-z0-9._:-]{1,255}\Z")
_USER = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")


class FieldError(ValueError):
    pass


def _luhn(digits: str) -> bool:
    total = 0
    for index, character in enumerate(reversed(digits)):
        value = int(character)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def clean_card_number(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) < 13 or len(digits) > 19 or not _luhn(digits):
        raise FieldError("卡号不正确")
    return digits


def clean_expiry(value: str) -> str:
    cleaned = value.strip()
    if re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", cleaned) is None:
        raise FieldError("有效期格式应为 MM/YY")
    return cleaned


def clean_cvv(value: str) -> str:
    cleaned = value.strip()
    if re.fullmatch(r"\d{3,4}", cleaned) is None:
        raise FieldError("安全码应为 3 或 4 位数字")
    return cleaned


def clean_text(value: str, label: str, limit: int, *, required: bool = True) -> str:
    cleaned = " ".join(value.split())
    if required and not cleaned:
        raise FieldError(f"请填写{label}")
    if len(cleaned) > limit:
        raise FieldError(f"{label}最长 {limit} 个字符")
    return cleaned


def clean_postal_code(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 20:
        raise FieldError("请填写邮编")
    return cleaned


def clean_holder(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > 80:
        raise FieldError("持卡人需要 1 到 80 个字符")
    return cleaned


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
