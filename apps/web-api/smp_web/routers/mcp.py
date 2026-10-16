"""MCP configuration for the signed-in user, and the MCP endpoint itself."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from smp_web.deps import SessionLocal, get_session, require_user
from smp_web.mcp_server import handle
from smp_web.schemas import McpSettingsIn, McpSettingsOut, McpTokenOut
from smpcore.models import McpSettings, utcnow

router = APIRouter()


def ensure_mcp_settings() -> None:
    with SessionLocal() as session:
        if session.get(McpSettings, 1) is None:
            session.add(
                McpSettings(
                    id=1,
                    enabled=False,
                    expose_servers=True,
                    expose_wallets=True,
                    expose_cards=True,
                )
            )
            session.commit()


def _row(session: Session) -> McpSettings:
    row = session.get(McpSettings, 1)
    if row is None:
        row = McpSettings(id=1, enabled=False, expose_servers=True, expose_wallets=True, expose_cards=True)
        session.add(row)
        session.commit()
    return row


def _public(row: McpSettings) -> dict:
    return {
        "enabled": row.enabled,
        "has_token": bool(row.token_hash),
        "token_last4": row.token_last4,
        "expose_servers": row.expose_servers,
        "expose_wallets": row.expose_wallets,
        "expose_cards": row.expose_cards,
    }


@router.get("/api/mcp", response_model=McpSettingsOut)
def read_settings(_: str = Depends(require_user), session: Session = Depends(get_session)) -> dict:
    return _public(_row(session))


@router.post("/api/mcp", response_model=McpSettingsOut)
def save_settings(
    body: McpSettingsIn,
    _: str = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict:
    row = _row(session)
    if body.enabled and not row.token_hash:
        raise HTTPException(status_code=422, detail="请先生成令牌")
    row.enabled = body.enabled
    row.expose_servers = body.expose_servers
    row.expose_wallets = body.expose_wallets
    row.expose_cards = body.expose_cards
    row.updated_at = utcnow()
    session.commit()
    return _public(row)


@router.post("/api/mcp/token", response_model=McpTokenOut)
def rotate_token(_: str = Depends(require_user), session: Session = Depends(get_session)) -> dict:
    raw = "smp_" + secrets.token_urlsafe(32)
    row = _row(session)
    row.token_hash = hashlib.sha256(raw.encode()).hexdigest()
    row.token_last4 = raw[-4:]
    row.updated_at = utcnow()
    session.commit()
    return {"token": raw, "token_last4": row.token_last4}


def _origin_ok(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    host = request.headers.get("host")
    return bool(host) and origin in {f"http://{host}", f"https://{host}"}


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return value.strip()


def _token_ok(row: McpSettings, token: str) -> bool:
    if not row.enabled or not row.token_hash or not token:
        return False
    digest = hashlib.sha256(token.encode()).hexdigest()
    return hmac.compare_digest(digest, row.token_hash)


@router.get("/mcp", include_in_schema=False)
def mcp_probe() -> Response:
    return JSONResponse({"detail": "请使用 POST"}, status_code=405, headers={"Allow": "POST"})


@router.post("/mcp", include_in_schema=False)
async def mcp_call(request: Request) -> Response:
    if not _origin_ok(request):
        return JSONResponse({"detail": "来源不被允许"}, status_code=403)
    with SessionLocal() as session:
        row = session.get(McpSettings, 1)
        if row is None or not _token_ok(row, _bearer(request)):
            return JSONResponse({"detail": "MCP 未开启或令牌不正确"}, status_code=401)
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "无法解析"}},
                status_code=400,
            )
        if not isinstance(payload, dict):
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "请求格式不正确"}},
                status_code=400,
            )
        status, body = handle(session, payload, row)
        if body is None:
            return Response(status_code=status)
        return JSONResponse(body, status_code=status)
