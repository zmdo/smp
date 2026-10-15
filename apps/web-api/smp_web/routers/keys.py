from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from smp_web.deps import get_session, require_user
from smp_web.key_store import store_private_key
from smp_web.schemas import SshKeyIn, SshKeyOut
from smpcore.models import Server, SshKey

router = APIRouter(prefix="/api/ssh-keys", dependencies=[Depends(require_user)])


@router.get("", response_model=list[SshKeyOut])
@router.get("/", response_model=list[SshKeyOut], include_in_schema=False)
def list_keys(session: Session = Depends(get_session)) -> list[dict]:
    server_count = (
        select(func.count(Server.id))
        .where(Server.ssh_key_id == SshKey.id)
        .correlate(SshKey)
        .scalar_subquery()
    )
    rows = session.execute(select(SshKey, server_count).order_by(SshKey.created_at.desc())).all()
    return [
        {
            "id": key.id,
            "name": key.name,
            "fingerprint": key.fingerprint,
            "server_count": int(count or 0),
            "created_at": key.created_at,
        }
        for key, count in rows
    ]


@router.post("", response_model=SshKeyOut, status_code=201)
def create_key(body: SshKeyIn, session: Session = Depends(get_session)) -> dict:
    key = store_private_key(session, body.secret, body.name)
    session.commit()
    session.refresh(key)
    count = session.scalar(select(func.count(Server.id)).where(Server.ssh_key_id == key.id))
    return {
        "id": key.id,
        "name": key.name,
        "fingerprint": key.fingerprint,
        "server_count": int(count or 0),
        "created_at": key.created_at,
    }


@router.delete("/{key_id}", status_code=204)
def delete_key(key_id: str, session: Session = Depends(get_session)) -> Response:
    try:
        parsed = uuid.UUID(key_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="密钥不存在") from exc
    key = session.get(SshKey, parsed)
    if key is None:
        raise HTTPException(status_code=404, detail="密钥不存在")
    used = session.scalar(select(func.count(Server.id)).where(Server.ssh_key_id == key.id)) or 0
    if used:
        raise HTTPException(status_code=409, detail=f"还有 {used} 台服务器在使用这个密钥")
    session.delete(key)
    session.commit()
    return Response(status_code=204)
