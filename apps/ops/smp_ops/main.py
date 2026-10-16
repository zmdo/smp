"""Ops service: encrypt secrets and run SSH jobs. It does not serve the website."""

from __future__ import annotations

import json
import logging
import secrets
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket
from pydantic import BaseModel, Field

from smp_ops.config import settings
from smp_ops.crypto import decrypt, encrypt, load_fernet
from smp_ops.metrics import metrics_loop
from smp_ops.ssh import OpsSSHError, fingerprint_of, load_private_key, preview_login
from smp_ops.terminal import serve_terminal
from smp_ops.worker import build_session_factory, schedule_loop, worker_loop
from smpcore.ensure import ensure_runtime_schema

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


class SshTestIn(BaseModel):
    host: str
    port: int
    username: str
    auth_method: str
    ciphertext: str = Field(min_length=1)


class SshTestOut(BaseModel):
    ok: bool
    message: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_schema(sessions.kw["bind"])
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
    threads.append(
        threading.Thread(
            target=metrics_loop,
            args=(stop, sessions, fernet),
            name="ops-metrics",
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


@app.post("/internal/ssh/test", response_model=SshTestOut, dependencies=[Depends(require_token)])
def test_ssh(body: SshTestIn) -> SshTestOut:
    try:
        secret = decrypt(fernet, body.ciphertext)
        message = preview_login(
            host=body.host,
            port=body.port,
            username=body.username,
            auth_method=body.auth_method,
            secret=secret,
        )
    except OpsSSHError as exc:
        return SshTestOut(ok=False, message=str(exc))
    except Exception:
        log.exception("ssh preview failed")
        return SshTestOut(ok=False, message="连接测试失败")
    return SshTestOut(ok=True, message=message)


class ExchangeBalanceIn(BaseModel):
    venue: str
    ciphertext: str = Field(min_length=1)


class ExchangeBalanceOut(BaseModel):
    balances: list[dict]


@app.post("/internal/exchange/balances", response_model=ExchangeBalanceOut, dependencies=[Depends(require_token)])
def exchange_balances(body: ExchangeBalanceIn) -> ExchangeBalanceOut:
    from smp_ops.exchanges import ExchangeError, fetch_balances

    try:
        raw = decrypt(fernet, body.ciphertext)
        credentials = json.loads(raw)
        if not isinstance(credentials, dict):
            raise ExchangeError("API 凭证无效")
        balances = fetch_balances(body.venue, credentials)
    except ExchangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="API 凭证无效") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="无法解密") from exc
    return ExchangeBalanceOut(balances=balances)


class MarketQuoteIn(BaseModel):
    venue: str
    symbol: str
    timeframe: str = "1h"


@app.post("/internal/markets/quote", dependencies=[Depends(require_token)])
def market_quote(body: MarketQuoteIn) -> dict:
    from smp_ops.exchanges import ExchangeError, fetch_quote

    try:
        return fetch_quote(body.venue, body.symbol, body.timeframe)
    except ExchangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.websocket("/internal/terminal/{server_id}")
async def terminal(websocket: WebSocket, server_id: str) -> None:
    token = websocket.headers.get("x-internal-token") or ""
    if not token or not secrets.compare_digest(token, settings.internal_token):
        await websocket.close(code=4401)
        return
    await serve_terminal(websocket, sessions, fernet, server_id)


@app.post("/internal/secrets/decrypt", response_model=DecryptOut, dependencies=[Depends(require_token)])
def decrypt_secret(body: DecryptIn) -> DecryptOut:
    try:
        return DecryptOut(plaintext=decrypt(fernet, body.ciphertext))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="无法解密") from exc
