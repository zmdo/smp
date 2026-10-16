"""Password vault for wallet mnemonics. The key never leaves this process."""

from __future__ import annotations

import base64
import json
import secrets

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session

from smpcore.models import Wallet

MEMORY_KIB = 65536
TIME_COST = 3
PARALLELISM = 1
KEY_LENGTH = 32


class VaultError(Exception):
    pass


def _key(password: str, salt: bytes, memory: int, time_cost: int, parallelism: int) -> bytes:
    return hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory,
        parallelism=parallelism,
        hash_len=KEY_LENGTH,
        type=Type.ID,
    )


def encrypt_mnemonic(password: str, mnemonic: str) -> str:
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = _key(password, salt, MEMORY_KIB, TIME_COST, PARALLELISM)
    ciphertext = AESGCM(key).encrypt(nonce, mnemonic.encode(), None)
    return json.dumps(
        {
            "v": 1,
            "kdf": "argon2id",
            "m": MEMORY_KIB,
            "t": TIME_COST,
            "p": PARALLELISM,
            "salt": base64.b64encode(salt).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "ct": base64.b64encode(ciphertext).decode(),
        },
        separators=(",", ":"),
    )


def decrypt_mnemonic(password: str, ciphertext: str) -> str:
    try:
        payload = json.loads(ciphertext)
        key = _key(
            password,
            base64.b64decode(payload["salt"]),
            int(payload["m"]),
            int(payload["t"]),
            int(payload["p"]),
        )
        plain = AESGCM(key).decrypt(base64.b64decode(payload["nonce"]), base64.b64decode(payload["ct"]), None)
    except (InvalidTag, KeyError, ValueError, TypeError) as exc:
        raise VaultError("钱包无法用当前密码解密") from exc
    return plain.decode()


def reencrypt_all(session: Session, old_password: str, new_password: str) -> None:
    wallets = list(session.scalars(select(Wallet)))
    opened = [(wallet, decrypt_mnemonic(old_password, wallet.ciphertext)) for wallet in wallets]
    for wallet, mnemonic in opened:
        wallet.ciphertext = encrypt_mnemonic(new_password, mnemonic)
