from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from smp_web.deps import get_session, require_user
from smp_web.schemas import ServerGroupIn, ServerGroupOut
from smp_web.validation import FieldError, clean_name
from smpcore.models import Server, ServerGroup

router = APIRouter(prefix="/api/server-groups", dependencies=[Depends(require_user)])

UNGROUPED_NAME = "未分组"


@router.get("", response_model=list[ServerGroupOut])
@router.get("/", response_model=list[ServerGroupOut], include_in_schema=False)
def list_groups(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(ServerGroup).order_by(ServerGroup.created_at, ServerGroup.name)).all()
    return [_out(row) for row in rows]


@router.post("", response_model=ServerGroupOut, status_code=201)
def create_group(body: ServerGroupIn, session: Session = Depends(get_session)) -> dict:
    try:
        name = clean_name(body.name)
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if name == UNGROUPED_NAME:
        raise HTTPException(status_code=422, detail="未分组是默认分组，不能再创建同名分组")
    group = ServerGroup(name=name)
    session.add(group)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="已有同名分组") from exc
    session.refresh(group)
    return _out(group)


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: str, session: Session = Depends(get_session)) -> Response:
    group = _get(session, group_id)
    for server in session.scalars(select(Server).where(Server.group_id == group.id)).all():
        server.group_id = None
    session.delete(group)
    session.commit()
    return Response(status_code=204)


def _get(session: Session, group_id: str) -> ServerGroup:
    try:
        parsed = uuid.UUID(group_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="分组不存在") from exc
    group = session.get(ServerGroup, parsed)
    if group is None:
        raise HTTPException(status_code=404, detail="分组不存在")
    return group


def _out(group: ServerGroup) -> dict:
    return {"id": group.id, "name": group.name, "created_at": group.created_at}
