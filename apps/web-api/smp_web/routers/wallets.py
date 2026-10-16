import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from smp_web.accounts import verify_password
from smp_web.deriver import DeriverError, derive, normalize_mnemonic
from smp_web.deps import get_session, require_user
from smp_web.schemas import WalletCreateIn, WalletCreatedOut, WalletDetailOut, WalletOut
from smp_web.validation import FieldError, clean_name
from smp_web.vault import encrypt_mnemonic
from smpcore.models import Account, Wallet, WalletAccount, WalletAddress

router = APIRouter(prefix="/api/wallets", dependencies=[Depends(require_user)])

CHAIN_LABELS = {
    "ethereum": "Ethereum",
    "bsc": "BNB Chain",
    "polygon": "Polygon",
    "arbitrum": "Arbitrum",
    "base": "Base",
    "bitcoin": "Bitcoin",
    "tron": "Tron",
    "solana": "Solana",
}
CHAIN_ORDER = list(CHAIN_LABELS)


def _password_ok(session: Session, username: str, password: str) -> None:
    account = session.scalar(select(Account).where(Account.username == username))
    if account is None or not verify_password(password, account.password_hash):
        raise HTTPException(status_code=401, detail="当前密码不正确")


def _checked_accounts(payload: dict) -> list[dict]:
    accounts = payload.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise HTTPException(status_code=503, detail="地址派生失败")
    checked = []
    for account in accounts:
        if not isinstance(account, dict) or not isinstance(account.get("index"), int):
            raise HTTPException(status_code=503, detail="地址派生失败")
        by_chain = {}
        for item in account.get("addresses") or []:
            if not isinstance(item, dict):
                raise HTTPException(status_code=503, detail="地址派生失败")
            chain = item.get("chain")
            address = item.get("address")
            path = item.get("path")
            if chain not in CHAIN_LABELS or not isinstance(address, str) or not address or len(address) > 128:
                raise HTTPException(status_code=503, detail="地址派生失败")
            if not isinstance(path, str) or len(path) > 80:
                raise HTTPException(status_code=503, detail="地址派生失败")
            by_chain[chain] = {"chain": chain, "address": address, "path": path}
        if set(by_chain) != set(CHAIN_ORDER):
            raise HTTPException(status_code=503, detail="地址派生失败")
        checked.append({"index": account["index"], "addresses": [by_chain[chain] for chain in CHAIN_ORDER]})
    return checked


@router.get("", response_model=list[WalletOut])
def list_wallets(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(Wallet).order_by(Wallet.created_at.desc()))
    return [{"id": wallet.id, "name": wallet.name, "created_at": wallet.created_at} for wallet in rows]


@router.get("/{wallet_id}", response_model=WalletDetailOut)
def get_wallet(wallet_id: uuid.UUID, session: Session = Depends(get_session)) -> WalletDetailOut:
    wallet = session.scalar(
        select(Wallet)
        .where(Wallet.id == wallet_id)
        .options(selectinload(Wallet.accounts).selectinload(WalletAccount.addresses))
    )
    if wallet is None:
        raise HTTPException(status_code=404, detail="钱包不存在")
    accounts = []
    for account in sorted(wallet.accounts, key=lambda item: item.derivation_index):
        addresses = sorted(account.addresses, key=lambda item: CHAIN_ORDER.index(item.chain) if item.chain in CHAIN_ORDER else 99)
        accounts.append(
            {
                "id": account.id,
                "name": account.name,
                "derivation_index": account.derivation_index,
                "addresses": [
                    {
                        "chain": item.chain,
                        "chain_label": CHAIN_LABELS.get(item.chain, item.chain),
                        "address": item.address,
                        "derivation_path": item.derivation_path,
                        "source": item.source,
                    }
                    for item in addresses
                ],
            }
        )
    return WalletDetailOut(
        id=wallet.id,
        name=wallet.name,
        created_at=wallet.created_at,
        accounts=accounts,
    )


@router.post("", response_model=WalletCreatedOut, response_model_exclude_none=True)
def create_wallet(
    body: WalletCreateIn,
    username: str = Depends(require_user),
    session: Session = Depends(get_session),
) -> WalletCreatedOut:
    try:
        name = clean_name(body.name)
    except FieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _password_ok(session, username, body.password)
    supplied = body.mnemonic if isinstance(body.mnemonic, str) else ""
    supplied = normalize_mnemonic(supplied)
    try:
        derived = derive(generate=not supplied, mnemonic=supplied or None, indices=[0])
    except DeriverError as exc:
        status = 422 if str(exc) in {"助记词不正确", "只接受 12 或 24 个单词"} else 503
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    if supplied:
        mnemonic = supplied
    else:
        generated = derived.get("mnemonic")
        mnemonic = normalize_mnemonic(generated) if isinstance(generated, str) else ""
    if not mnemonic:
        raise HTTPException(status_code=503, detail="地址派生失败")
    word_count = derived.get("word_count")
    if word_count not in (12, 24) or len(mnemonic.split()) != word_count:
        raise HTTPException(status_code=503, detail="地址派生失败")
    digest = hashlib.sha256(mnemonic.encode()).hexdigest()
    if session.scalar(select(Wallet.id).where(Wallet.mnemonic_sha256 == digest)) is not None:
        raise HTTPException(status_code=409, detail="这个助记词已经添加过")
    wallet = Wallet(
        name=name,
        ciphertext=encrypt_mnemonic(body.password, mnemonic),
        mnemonic_sha256=digest,
        word_count=word_count,
    )
    session.add(wallet)
    session.flush()
    for account in _checked_accounts(derived):
        row = WalletAccount(
            wallet_id=wallet.id,
            name=f"Account {account['index'] + 1}",
            derivation_index=account["index"],
        )
        session.add(row)
        session.flush()
        for item in account["addresses"]:
            session.add(
                WalletAddress(
                    wallet_id=wallet.id,
                    account_id=row.id,
                    chain=item["chain"],
                    address=item["address"],
                    derivation_path=item["path"],
                    source="derived",
                )
            )
    session.commit()
    session.refresh(wallet)
    return WalletCreatedOut(
        id=wallet.id,
        name=wallet.name,
        created_at=wallet.created_at,
        mnemonic=None if supplied else mnemonic,
    )
