from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from smp_web.deps import get_session, require_user
from smp_web.schemas import ExchangeIn, ExchangeOut, ExchangeVenueOut
from smp_web.secrets_client import encrypt_secret, exchange_balances
from smp_web.validation import FieldError, clean_name
from smpcore.exchanges import VENUES, clean_credentials, venue_by_id
from smpcore.models import ExchangeAccount

router = APIRouter(prefix="/api/exchanges", dependencies=[Depends(require_user)])


@router.get("/venues", response_model=list[ExchangeVenueOut])
def list_venues() -> list[dict]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "wallet": item.wallet,
            "fields": [{"key": field.key, "label": field.label} for field in item.fields],
        }
        for item in VENUES
    ]


@router.get("", response_model=list[ExchangeOut])
@router.get("/", response_model=list[ExchangeOut], include_in_schema=False)
def list_exchanges(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(ExchangeAccount).order_by(ExchangeAccount.created_at.desc())).all()
    return [_out(row) for row in rows]


@router.post("", response_model=ExchangeOut, status_code=201)
def create_exchange(body: ExchangeIn, session: Session = Depends(get_session)) -> dict:
    account = ExchangeAccount(
        name=_name(body.name),
        venue=_venue(body.venue).id,
        secret_ciphertext=_encrypt(body.venue, body.credentials),
        balances="[]",
        balance_error="",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    _refresh(session, account)
    return _out(account)


@router.post("/{exchange_id}/refresh", response_model=ExchangeOut)
def refresh_exchange(exchange_id: str, session: Session = Depends(get_session)) -> dict:
    account = _get(session, exchange_id)
    _refresh(session, account)
    return _out(account)


@router.delete("/{exchange_id}", status_code=204)
def delete_exchange(exchange_id: str, session: Session = Depends(get_session)) -> Response:
    account = _get(session, exchange_id)
    session.delete(account)
    session.commit()
    return Response(status_code=204)


def _refresh(session: Session, account: ExchangeAccount) -> None:
    try:
        balances = exchange_balances(account.venue, account.secret_ciphertext)
    except HTTPException as exc:
        account.balance_error = exc.detail if isinstance(exc.detail, str) else "查询余额失败"
        account.checked_at = datetime.now(timezone.utc)
        session.commit()
        return
    account.balances = json.dumps(balances, ensure_ascii=False)
    account.balance_error = ""
    account.checked_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(account)


def _encrypt(venue: str, credentials: dict[str, str]) -> str:
    try:
        cleaned = clean_credentials(venue, credentials)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ciphertext, _fingerprint = encrypt_secret(json.dumps(cleaned, ensure_ascii=False), "password")
    return ciphertext


def _name(value: str) -> str:
    try:
        return clean_name(value)
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _venue(venue: str):
    try:
        return venue_by_id(venue)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _get(session: Session, exchange_id: str) -> ExchangeAccount:
    try:
        parsed = uuid.UUID(exchange_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="交易所不存在") from exc
    account = session.get(ExchangeAccount, parsed)
    if account is None:
        raise HTTPException(status_code=404, detail="交易所不存在")
    return account


def _balances(raw: str) -> list[dict]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "asset": str(item.get("asset") or ""),
                "free": str(item.get("free") or "0"),
                "locked": str(item.get("locked") or "0"),
                "total": str(item.get("total") or "0"),
            }
        )
    return rows


def _out(account: ExchangeAccount) -> dict:
    try:
        spec = venue_by_id(account.venue)
        venue_name, wallet = spec.name, spec.wallet
    except ValueError:
        venue_name, wallet = account.venue, ""
    return {
        "id": account.id,
        "name": account.name,
        "venue": account.venue,
        "venue_name": venue_name,
        "wallet": wallet,
        "balances": _balances(account.balances),
        "balance_error": account.balance_error,
        "checked_at": account.checked_at,
        "created_at": account.created_at,
    }
