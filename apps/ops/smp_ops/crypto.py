"""Encrypt SSH secrets. The Fernet key stays in this service."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


def load_fernet(key: str | None, key_file: str) -> Fernet:
    if key:
        return Fernet(key.encode())
    directory = os.path.dirname(key_file) or "."
    os.makedirs(directory, exist_ok=True)
    if not os.path.exists(key_file):
        with open(key_file, "wb") as handle:
            handle.write(Fernet.generate_key())
        try:
            os.chmod(key_file, 0o600)
        except OSError:
            pass
    with open(key_file, "rb") as handle:
        stored = handle.read().strip()
    return Fernet(stored)


def encrypt(fernet: Fernet, plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt(fernet: Fernet, ciphertext: str) -> str:
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("无法解密 SSH 密钥，加密主密钥与写入时不一致。") from exc
