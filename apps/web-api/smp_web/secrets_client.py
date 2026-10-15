from __future__ import annotations

import httpx
from fastapi import HTTPException

from smp_web.config import settings


def encrypt_secret(plaintext: str, auth_method: str) -> tuple[str, str | None]:
    try:
        response = httpx.post(
            f"{settings.ops_url.rstrip('/')}/internal/secrets/encrypt",
            json={"plaintext": plaintext, "auth_method": auth_method},
            headers={"X-Internal-Token": settings.internal_token},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="运维服务不可用，没有保存") from exc
    if response.status_code >= 400:
        detail = "密钥无效"
        if "application/json" in response.headers.get("content-type", ""):
            payload = response.json().get("detail")
            if isinstance(payload, str):
                detail = payload
        raise HTTPException(status_code=422, detail=detail)
    body = response.json()
    ciphertext = body.get("ciphertext")
    fingerprint = body.get("fingerprint")
    if not isinstance(ciphertext, str) or not ciphertext:
        raise HTTPException(status_code=503, detail="运维服务没有返回加密结果")
    if auth_method == "private_key" and not isinstance(fingerprint, str):
        raise HTTPException(status_code=503, detail="运维服务没有返回密钥指纹")
    return ciphertext, fingerprint if isinstance(fingerprint, str) else None


def decrypt_secret(ciphertext: str) -> str:
    try:
        response = httpx.post(
            f"{settings.ops_url.rstrip('/')}/internal/secrets/decrypt",
            json={"ciphertext": ciphertext},
            headers={"X-Internal-Token": settings.internal_token},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="运维服务不可用，无法查看") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="运维服务无法解密")
    plaintext = response.json().get("plaintext")
    if not isinstance(plaintext, str):
        raise HTTPException(status_code=503, detail="运维服务没有返回解密结果")
    return plaintext
