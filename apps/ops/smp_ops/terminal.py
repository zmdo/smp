"""Interactive SSH shell for a registered server."""

from __future__ import annotations

import asyncio
import json
import socket
import uuid

from cryptography.fernet import Fernet
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.orm import sessionmaker

from smp_ops.crypto import decrypt
from smp_ops.ssh import OpsSSHError, connect
from smp_ops.worker import _ciphertext
from smpcore.models import Server


def open_shell(sessions: sessionmaker, fernet: Fernet, server_id: str):
    try:
        parsed = uuid.UUID(server_id)
    except ValueError as exc:
        raise OpsSSHError("服务器不存在") from exc
    with sessions() as session:
        server = session.get(Server, parsed)
        if server is None:
            raise OpsSSHError("服务器不存在")
        secret = decrypt(fernet, _ciphertext(session, server))
        host = server.intranet_host
        port = server.ssh_port
        username = server.ssh_user
        auth_method = server.auth_method
        expected = server.host_key_fingerprint
    client, _policy = connect(
        host=host,
        port=port,
        username=username,
        auth_method=auth_method,
        secret=secret,
        expected_fingerprint=expected,
    )
    channel = client.invoke_shell(term="xterm-256color", width=80, height=24)
    channel.settimeout(0.2)
    return client, channel


async def serve_terminal(websocket: WebSocket, sessions: sessionmaker, fernet: Fernet, server_id: str) -> None:
    await websocket.accept()
    loop = asyncio.get_running_loop()
    try:
        client, channel = await loop.run_in_executor(None, open_shell, sessions, fernet, server_id)
    except (OpsSSHError, ValueError) as exc:
        await websocket.send_text(f"\r\n{exc}\r\n")
        await websocket.close()
        return

    async def read_shell() -> None:
        while True:
            try:
                data = await loop.run_in_executor(None, channel.recv, 65536)
            except socket.timeout:
                if channel.closed:
                    break
                continue
            except Exception:
                break
            if not data:
                break
            await websocket.send_bytes(data)

    async def write_shell() -> None:
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break
            if message["type"] == "websocket.disconnect":
                break
            if message.get("bytes"):
                channel.send(message["bytes"])
                continue
            text = message.get("text")
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if payload.get("type") != "resize":
                continue
            cols = max(20, min(int(payload.get("cols") or 80), 300))
            rows = max(5, min(int(payload.get("rows") or 24), 120))
            channel.resize_pty(width=cols, height=rows)

    tasks = [asyncio.create_task(read_shell()), asyncio.create_task(write_shell())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        channel.close()
        client.close()
