import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from smp_web.deps import get_session, require_user
from smp_web.schemas import VirtualCardIn, VirtualCardOut, VirtualCardSecretOut
from smp_web.secrets_client import decrypt_secret, encrypt_secret
from smp_web.validation import FieldError, clean_card_number, clean_cvv, clean_expiry, clean_holder, clean_name
from smpcore.models import VirtualCard

router = APIRouter(prefix="/api/cards", dependencies=[Depends(require_user)])


def _card(session: Session, card_id: str) -> VirtualCard:
    try:
        parsed = uuid.UUID(card_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="信用卡不存在") from exc
    card = session.get(VirtualCard, parsed)
    if card is None:
        raise HTTPException(status_code=404, detail="信用卡不存在")
    return card


def _checked(body: VirtualCardIn) -> tuple[str, str, str, str, str, str]:
    try:
        return (
            clean_name(body.name),
            clean_holder(body.holder),
            clean_card_number(body.number),
            clean_expiry(body.expiry),
            clean_cvv(body.cvv),
            body.note.strip(),
        )
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _out(card: VirtualCard) -> dict:
    return {
        "id": card.id,
        "name": card.name,
        "holder": card.holder,
        "expiry": card.expiry,
        "last4": card.last4,
        "note": card.note,
        "created_at": card.created_at,
    }


@router.get("", response_model=list[VirtualCardOut])
def list_cards(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(VirtualCard).order_by(VirtualCard.created_at.desc()))
    return [_out(card) for card in rows]


@router.post("", response_model=VirtualCardOut, status_code=201)
def create_card(body: VirtualCardIn, session: Session = Depends(get_session)) -> dict:
    name, holder, number, expiry, cvv, note = _checked(body)
    if len(note) > 500:
        raise HTTPException(status_code=422, detail="备注最长 500 个字符")
    number_ciphertext, _ = encrypt_secret(number, "password")
    cvv_ciphertext, _ = encrypt_secret(cvv, "password")
    card = VirtualCard(
        name=name,
        holder=holder,
        expiry=expiry,
        last4=number[-4:],
        number_ciphertext=number_ciphertext,
        cvv_ciphertext=cvv_ciphertext,
        note=note,
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
