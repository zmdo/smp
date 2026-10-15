from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from smp_web.secrets_client import encrypt_secret
from smp_web.validation import FieldError, clean_name
from smpcore.models import SshKey


def store_private_key(session: Session, secret: str, name: str | None) -> SshKey:
    cleaned = secret.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="请粘贴私钥")
    ciphertext, fingerprint = encrypt_secret(cleaned, "private_key")
    if fingerprint is None:
        raise HTTPException(status_code=503, detail="运维服务没有返回密钥指纹")
    existing = session.scalar(select(SshKey).where(SshKey.fingerprint == fingerprint))
    if existing is not None:
        return existing
    try:
        label = clean_name(name) if name and name.strip() else f"密钥 {fingerprint[-8:]}"
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    key = SshKey(name=label, fingerprint=fingerprint, secret_ciphertext=ciphertext)
    session.add(key)
    session.flush()
    return key


def require_key(session: Session, key_id: uuid.UUID) -> SshKey:
    key = session.get(SshKey, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="密钥不存在")
    return key
