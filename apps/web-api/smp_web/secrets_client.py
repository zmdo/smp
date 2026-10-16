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


def test_ssh(host: str, port: int, username: str, auth_method: str, ciphertext: str) -> dict[str, object]:
    try:
        response = httpx.post(
            f"{settings.ops_url.rstrip('/')}/internal/ssh/test",
            json={
                "host": host,
                "port": port,
                "username": username,
                "auth_method": auth_method,
                "ciphertext": ciphertext,
            },
            headers={"X-Internal-Token": settings.internal_token},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="运维服务不可用") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="运维服务不可用")
    body = response.json()
    message = body.get("message")
    return {"ok": bool(body.get("ok")), "message": message if isinstance(message, str) else "连接测试失败"}


def exchange_balances(venue: str, ciphertext: str) -> list[dict]:
    try:
        response = httpx.post(
            f"{settings.ops_url.rstrip('/')}/internal/exchange/balances",
            json={"venue": venue, "ciphertext": ciphertext},
            headers={"X-Internal-Token": settings.internal_token},
            timeout=40,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="运维服务不可用") from exc
    if response.status_code == 422:
        detail = "查询余额失败"
        if "application/json" in response.headers.get("content-type", ""):
            payload = response.json().get("detail")
            if isinstance(payload, str) and payload:
                detail = payload
        raise HTTPException(status_code=422, detail=detail)
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="运维服务不可用")
    balances = response.json().get("balances")
    if not isinstance(balances, list):
        raise HTTPException(status_code=503, detail="运维服务没有返回余额")
    return [item for item in balances if isinstance(item, dict)]


def market_quote(venue: str, symbol: str, timeframe: str) -> dict:
    try:
        response = httpx.post(
            f"{settings.ops_url.rstrip('/')}/internal/markets/quote",
            json={"venue": venue, "symbol": symbol, "timeframe": timeframe},
            headers={"X-Internal-Token": settings.internal_token},
            timeout=40,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="运维服务不可用") from exc
    if response.status_code == 422:
        detail = "查询行情失败"
        if "application/json" in response.headers.get("content-type", ""):
            payload = response.json().get("detail")
            if isinstance(payload, str) and payload:
                detail = payload
        raise HTTPException(status_code=422, detail=detail)
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="运维服务不可用")
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("candles"), list):
        raise HTTPException(status_code=503, detail="运维服务没有返回行情")
    return body
