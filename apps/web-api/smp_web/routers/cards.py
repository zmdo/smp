import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from smp_web.deps import get_session, require_user
from smp_web.schemas import VirtualCardIn, VirtualCardOut, VirtualCardSecretOut
from smp_web.secrets_client import decrypt_secret, encrypt_secret
from smp_web.validation import (
    FieldError,
    clean_card_number,
    clean_cvv,
    clean_expiry,
    clean_holder,
    clean_name,
    clean_postal_code,
    clean_text,
)
from smpcore.models import VirtualCard

router = APIRouter(prefix="/api/cards", dependencies=[Depends(require_user)])

_CARD_COLUMNS = {
    "platform": "VARCHAR(80) NOT NULL DEFAULT ''",
    "country": "VARCHAR(80) NOT NULL DEFAULT ''",
    "region": "VARCHAR(80) NOT NULL DEFAULT ''",
    "city": "VARCHAR(80) NOT NULL DEFAULT ''",
    "address1": "VARCHAR(160) NOT NULL DEFAULT ''",
    "address2": "VARCHAR(160) NOT NULL DEFAULT ''",
    "postal_code": "VARCHAR(20) NOT NULL DEFAULT ''",
}


def ensure_virtual_card_columns() -> None:
    from sqlalchemy import inspect, text

    from smp_web.deps import engine

    inspector = inspect(engine)
    if "virtual_cards" not in set(inspector.get_table_names()):
        return
    present = {column["name"] for column in inspector.get_columns("virtual_cards")}
    missing = [name for name in _CARD_COLUMNS if name not in present]
    if not missing:
        return
    with engine.begin() as connection:
        for name in missing:
            connection.execute(text(f"ALTER TABLE virtual_cards ADD COLUMN {name} {_CARD_COLUMNS[name]}"))


def _card(session: Session, card_id: str) -> VirtualCard:
    try:
        parsed = uuid.UUID(card_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="信用卡不存在") from exc
    card = session.get(VirtualCard, parsed)
    if card is None:
        raise HTTPException(status_code=404, detail="信用卡不存在")
    return card


def _checked(body: VirtualCardIn) -> dict[str, str]:
    try:
        note = body.note.strip()
        if len(note) > 500:
            raise FieldError("备注最长 500 个字符")
        return {
            "name": clean_name(body.name),
            "platform": clean_text(body.platform, "平台", 80),
            "holder": clean_holder(body.holder),
            "number": clean_card_number(body.number),
            "expiry": clean_expiry(body.expiry),
            "cvv": clean_cvv(body.cvv),
            "country": clean_text(body.country, "国家", 80),
            "region": clean_text(body.region, "地区/州", 80),
            "city": clean_text(body.city, "市", 80),
            "address1": clean_text(body.address1, "地址1", 160),
            "address2": clean_text(body.address2, "地址2", 160, required=False),
            "postal_code": clean_postal_code(body.postal_code),
            "note": note,
        }
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _out(card: VirtualCard) -> dict:
    return {
        "id": card.id,
        "name": card.name,
        "platform": card.platform,
        "holder": card.holder,
        "expiry": card.expiry,
        "last4": card.last4,
        "country": card.country,
        "region": card.region,
        "city": card.city,
        "address1": card.address1,
        "address2": card.address2,
        "postal_code": card.postal_code,
        "note": card.note,
        "created_at": card.created_at,
    }


@router.get("", response_model=list[VirtualCardOut])
def list_cards(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(VirtualCard).order_by(VirtualCard.created_at.desc()))
    return [_out(card) for card in rows]


@router.post("", response_model=VirtualCardOut, status_code=201)
def create_card(body: VirtualCardIn, session: Session = Depends(get_session)) -> dict:
    fields = _checked(body)
    number = fields.pop("number")
    cvv = fields.pop("cvv")
    number_ciphertext, _ = encrypt_secret(number, "password")
    cvv_ciphertext, _ = encrypt_secret(cvv, "password")
    card = VirtualCard(
        **fields,
        last4=number[-4:],
        number_ciphertext=number_ciphertext,
        cvv_ciphertext=cvv_ciphertext,
    )
    session.add(card)
    session.commit()
    session.refresh(card)
    return _out(card)


@router.get("/{card_id}/secret", response_model=VirtualCardSecretOut)
def reveal_card(card_id: str, session: Session = Depends(get_session)) -> VirtualCardSecretOut:
    card = _card(session, card_id)
    return VirtualCardSecretOut(
        number=decrypt_secret(card.number_ciphertext),
        cvv=decrypt_secret(card.cvv_ciphertext),
    )


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: str, session: Session = Depends(get_session)) -> Response:
    card = _card(session, card_id)
    session.delete(card)
    session.commit()
    return Response(status_code=204)
