"""Time-based one-time passwords for console login."""

from __future__ import annotations

import pyotp


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, username: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="策略控制台")


def verify_code(secret: str, code: str) -> bool:
    cleaned = code.strip().replace(" ", "")
    if len(cleaned) != 6 or not cleaned.isdigit():
        return False
    return bool(pyotp.TOTP(secret).verify(cleaned, valid_window=1))
