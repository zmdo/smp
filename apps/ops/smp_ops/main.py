"""Ops service: encrypt secrets and run SSH jobs. It does not serve the website."""

from __future__ import annotations

import logging
import secrets
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from smp_ops.config import settings
from smp_ops.crypto import decrypt, encrypt, load_fernet
from smp_ops.ssh import OpsSSHError, fingerprint_of, load_private_key
from smp_ops.worker import build_session_factory, schedule_loop, worker_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("smp.ops")

fernet = load_fernet(settings.encryption_key, settings.encryption_key_file)
sessions = build_session_factory(settings.database_url)


def require_token(x_internal_token: str = Header()) -> None:
    if not secrets.compare_digest(x_internal_token, settings.internal_token):
        raise HTTPException(status_code=401, detail="内部调用凭证无效")


class EncryptIn(BaseModel):
    plaintext: str = Field(min_length=1)
    auth_method: str


class EncryptOut(BaseModel):
    ciphertext: str
    fingerprint: str | None = None


class DecryptIn(BaseModel):
    ciphertext: str = Field(min_length=1)


class DecryptOut(BaseModel):
    plaintext: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop = threading.Event()
    threads = [
        threading.Thread(target=worker_loop, args=(stop, sessions, fernet), name=f"ops-worker-{index}", daemon=True)
        for index in range(4)
    ]
    threads.append(
        threading.Thread(
            target=schedule_loop,
            args=(stop, sessions, settings.inspect_interval_seconds),
            name="ops-scheduler",
            daemon=True,
        )
    )
    for thread in threads:
        thread.start()
    log.info("ops worker started")
    yield
    stop.set()


app = FastAPI(title="smp-ops", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/secrets/encrypt", response_model=EncryptOut, dependencies=[Depends(require_token)])
def encrypt_secret(body: EncryptIn) -> EncryptOut:
    fingerprint = None
    if body.auth_method == "private_key":
        try:
            key = load_private_key(body.plaintext.strip())
        except OpsSSHError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        plaintext = body.plaintext.strip()
        fingerprint = fingerprint_of(key)
    elif body.auth_method == "password":
        if not body.plaintext.strip():
            raise HTTPException(status_code=422, detail="口令不能为空")
        plaintext = body.plaintext
    else:
        raise HTTPException(status_code=422, detail="认证方式只能是私钥或口令")
    return EncryptOut(ciphertext=encrypt(fernet, plaintext), fingerprint=fingerprint)


@app.post("/internal/secrets/decrypt", response_model=DecryptOut, dependencies=[Depends(require_token)])
def decrypt_secret(body: DecryptIn) -> DecryptOut:
    try:
        return DecryptOut(plaintext=decrypt(fernet, body.ciphertext))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="无法解密") from exc
