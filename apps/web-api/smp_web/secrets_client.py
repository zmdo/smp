from __future__ import annotations

import httpx
from fastapi import HTTPException

from smp_web.config import settings


def encrypt_secret(plaintext: str, auth_method: str) -> str:
    try:
        response = httpx.post(
            f"{settings.ops_url.rstrip('/')}/internal/secrets/encrypt",
            json={"plaintext": plaintext, "auth_method": auth_method},
            headers={"X-Internal-Token": settings.internal_token},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="运维服务不可用，没有保存这台服务器") from exc
    if response.status_code >= 400:
        detail = "密钥无效"
        if "application/json" in response.headers.get("content-type", ""):
            payload = response.json().get("detail")
            if isinstance(payload, str):
                detail = payload
        raise HTTPException(status_code=422, detail=detail)
    ciphertext = response.json().get("ciphertext")
    if not isinstance(ciphertext, str) or not ciphertext:
        raise HTTPException(status_code=503, detail="运维服务没有返回加密结果")
    return ciphertext
