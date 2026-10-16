"""Read-only MCP endpoint for the console.

Callers authenticate with a bearer token from 平台设置 / MCP. Responses never
include card numbers, CVVs, mnemonics, or SSH secrets.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from smpcore.models import McpSettings, Server, VirtualCard, Wallet, WalletAccount

PROTOCOL_VERSIONS = ("2025-03-26", "2024-11-05")
SERVER_NAME = "策略控制台"
SERVER_VERSION = "0.1.0"


def handle(session: Session, message: dict[str, Any], row: McpSettings) -> tuple[int, dict[str, Any] | None]:
    if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return 400, _error(message.get("id"), -32600, "请求格式不正确")
    method = message["method"]
    request_id = message.get("id")
    if method.startswith("notifications/") or request_id is None and method != "initialize":
        return 202, None
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return 400, _error(request_id, -32602, "参数格式不正确")
    if method == "initialize":
        version = params.get("protocolVersion")
        chosen = version if version in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return 200, _result(
            request_id,
            {
                "protocolVersion": chosen,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "只读。不会返回卡号、安全码、助记词或 SSH 私钥。",
            },
        )
    if method == "ping":
        return 200, _result(request_id, {})
    if method == "tools/list":
        return 200, _result(request_id, {"tools": _tools(row)})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return 400, _error(request_id, -32602, "参数格式不正确")
        return 200, _result(request_id, _call(session, row, name, arguments))
    return 400, _error(request_id, -32601, "方法不存在")


def _tools(row: McpSettings) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    if row.expose_servers:
        tools.append(
            {
                "name": "list_servers",
                "description": "列出已登记的服务器，不含 SSH 密钥或口令。",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        )
        tools.append(
            {
                "name": "list_containers",
                "description": "列出一台服务器上最近一次巡检看到的容器。",
                "inputSchema": {
                    "type": "object",
                    "properties": {"server": {"type": "string", "description": "服务器名称"}},
                    "required": ["server"],
                    "additionalProperties": False,
                },
            }
        )
    if row.expose_wallets:
        tools.append(
            {
                "name": "list_wallets",
                "description": "列出钱包名称和收款地址，不含助记词。",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        )
    if row.expose_cards:
        tools.append(
            {
                "name": "list_cards",
                "description": "列出虚拟信用卡摘要，只有尾号，没有完整卡号和安全码。",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        )
    return tools


def _call(session: Session, row: McpSettings, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    allowed = {tool["name"] for tool in _tools(row)}
    if name not in allowed:
        return _tool_error("该工具未开放")
    if name == "list_servers":
        return _tool_text(_servers(session))
    if name == "list_containers":
        server_name = arguments.get("server")
        if not isinstance(server_name, str) or not server_name.strip():
            return _tool_error("需要提供服务器名称")
        found = _containers(session, server_name.strip())
        if found is None:
            return _tool_error("服务器不存在")
        return _tool_text(found)
    if name == "list_wallets":
        return _tool_text(_wallets(session))
    if name == "list_cards":
        return _tool_text(_cards(session))
    return _tool_error("该工具未开放")


def _servers(session: Session) -> list[dict[str, Any]]:
    rows = session.scalars(select(Server).order_by(Server.created_at.desc()))
    return [
        {
            "name": item.name,
            "address": item.intranet_host,
            "ssh_port": item.ssh_port,
            "ssh_user": item.ssh_user,
            "reachability": item.reachability,
            "docker_version": item.docker_version,
        }
        for item in rows
    ]


def _containers(session: Session, server_name: str) -> dict[str, Any] | None:
    server = session.scalar(
        select(Server).where(Server.name == server_name).options(selectinload(Server.containers))
    )
    if server is None:
        return None
    return {
        "server": server.name,
        "containers": [
            {"name": item.name, "image": item.image, "status": item.status, "ports": item.ports}
            for item in server.containers
        ],
    }


def _wallets(session: Session) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Wallet)
        .order_by(Wallet.created_at.desc())
        .options(selectinload(Wallet.accounts).selectinload(WalletAccount.addresses))
    )
    listed = []
    for wallet in rows:
        accounts = []
        for account in sorted(wallet.accounts, key=lambda item: item.derivation_index):
            accounts.append(
                {
                    "name": account.name,
                    "addresses": [
                        {
                            "chain": item.chain,
                            "address": item.address,
                            "derivation_path": item.derivation_path,
                        }
                        for item in account.addresses
                    ],
                }
            )
        listed.append({"name": wallet.name, "accounts": accounts})
    return listed


def _cards(session: Session) -> list[dict[str, Any]]:
    rows = session.scalars(select(VirtualCard).order_by(VirtualCard.created_at.desc()))
    return [
        {
            "name": item.name,
            "platform": item.platform,
            "holder": item.holder,
            "last4": item.last4,
            "expiry": item.expiry,
            "country": item.country,
            "region": item.region,
            "city": item.city,
            "address1": item.address1,
            "address2": item.address2,
            "postal_code": item.postal_code,
        }
        for item in rows
    ]


def _tool_text(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": False}


def _tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
