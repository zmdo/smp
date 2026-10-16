"""Browser terminal proxied to the ops SSH shell."""

from __future__ import annotations

import asyncio
import uuid

import websockets
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select

from smp_web.config import settings
from smp_web.deps import SessionLocal
from smpcore.models import Account, Server

router = APIRouter()


def _ops_ws(path: str) -> str:
    base = settings.ops_url.rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://") :]
    return base + path


@router.websocket("/api/servers/{server_id}/terminal")
async def terminal(websocket: WebSocket, server_id: str) -> None:
    session = websocket.scope.get("session") or {}
    username = session.get("user")
    try:
        parsed = uuid.UUID(server_id)
    except ValueError:
        parsed = None
    with SessionLocal() as db:
        account = None
        if isinstance(username, str) and username:
            account = db.scalar(select(Account.id).where(Account.username == username))
        server = db.get(Server, parsed) if parsed is not None else None
    if account is None or server is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        upstream = await websockets.connect(
            _ops_ws(f"/internal/terminal/{server_id}"),
            additional_headers={"X-Internal-Token": settings.internal_token},
        )
    except Exception:
        await websocket.send_text("\r\n运维服务不可用。\r\n")
        await websocket.close()
        return

    async def read_ops() -> None:
        async for message in upstream:
            if isinstance(message, bytes):
                await websocket.send_bytes(message)
            else:
                await websocket.send_text(message)

    async def write_ops() -> None:
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break
            if message["type"] == "websocket.disconnect":
                break
            if message.get("bytes") is not None:
                await upstream.send(message["bytes"])
            elif message.get("text"):
                await upstream.send(message["text"])

    tasks = [asyncio.create_task(read_ops()), asyncio.create_task(write_ops())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await upstream.close()
        await websocket.close()
