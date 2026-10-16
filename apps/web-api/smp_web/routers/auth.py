from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from smp_web.accounts import hash_password, verify_password
from smp_web.vault import VaultError, reencrypt_all
from smp_web.deps import get_session, require_user
from smp_web.schemas import (
    LoginIn,
    LoginOut,
    MeOut,
    PasswordChangeIn,
    UsernameChangeIn,
    TotpCodeIn,
    TotpDisableIn,
    TotpSetupOut,
)
from smp_web.totp import new_secret, provisioning_uri, verify_code
from smpcore.models import Account

router = APIRouter(prefix="/api/auth")


def _account(session: Session, username: str) -> Account | None:
    return session.scalar(select(Account).where(Account.username == username))


def _current(session: Session, username: str) -> Account:
    account = _account(session, username)
    if account is None:
        raise HTTPException(status_code=401, detail="未登录")
    return account


def _me(request: Request, session: Session) -> MeOut:
    username = request.session.get("user")
    account = _account(session, username) if isinstance(username, str) else None
    if account is None:
        return MeOut(authenticated=False, password_is_default=False, totp_enabled=False)
    return MeOut(
        authenticated=True,
        username=account.username,
        password_is_default=verify_password("changeme", account.password_hash),
        totp_enabled=account.totp_enabled,
    )


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, request: Request, session: Session = Depends(get_session)) -> LoginOut:
    account = _account(session, body.username.strip())
    if account is None or not verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    if account.totp_enabled:
        if not body.totp_code or not body.totp_code.strip():
            return LoginOut(ok=False, totp_required=True)
        if account.totp_secret is None or not verify_code(account.totp_secret, body.totp_code):
            raise HTTPException(status_code=401, detail="验证码不正确")
    request.session["user"] = account.username
    return LoginOut(ok=True)


@router.post("/logout")
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/me", response_model=MeOut)
def me(request: Request, session: Session = Depends(get_session)) -> MeOut:
    return _me(request, session)


@router.get("/session", dependencies=[Depends(require_user)])
def session_ok() -> dict[str, bool]:
    return {"ok": True}


@router.post("/username", dependencies=[Depends(require_user)])
def change_username(
    body: UsernameChangeIn,
    request: Request,
    username: str = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    account = _current(session, username)
    cleaned = body.username.strip()
    if not cleaned or any(character.isspace() for character in cleaned):
        raise HTTPException(status_code=422, detail="用户名不能包含空格")
    if cleaned == account.username:
        return {"username": cleaned}
    account.username = cleaned
    session.commit()
    request.session["user"] = cleaned
    return {"username": cleaned}


@router.post("/password", dependencies=[Depends(require_user)])
def change_password(
    body: PasswordChangeIn,
    username: str = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    account = _current(session, username)
    if not verify_password(body.current_password, account.password_hash):
        raise HTTPException(status_code=401, detail="当前密码不正确")
    if len(body.new_password.encode()) > 72:
        raise HTTPException(status_code=422, detail="新密码最长 72 字节")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=422, detail="新密码需要和当前密码不同")
    try:
        reencrypt_all(session, body.current_password, body.new_password)
    except VaultError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="钱包无法用当前密码解密，密码没有修改") from exc
    account.password_hash = hash_password(body.new_password)
    session.commit()
    return {"ok": True}


@router.post("/totp/setup", response_model=TotpSetupOut, dependencies=[Depends(require_user)])
def setup_totp(username: str = Depends(require_user), session: Session = Depends(get_session)) -> TotpSetupOut:
    account = _current(session, username)
    if account.totp_enabled:
        raise HTTPException(status_code=409, detail="两步验证已经开启")
    secret = new_secret()
    account.totp_pending_secret = secret
    session.commit()
    return TotpSetupOut(secret=secret, otpauth_uri=provisioning_uri(secret, account.username))


@router.post("/totp/confirm", dependencies=[Depends(require_user)])
def confirm_totp(
    body: TotpCodeIn,
    username: str = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    account = _current(session, username)
    if account.totp_enabled:
        raise HTTPException(status_code=409, detail="两步验证已经开启")
    if not account.totp_pending_secret or not verify_code(account.totp_pending_secret, body.code):
        raise HTTPException(status_code=401, detail="验证码不正确")
    account.totp_secret = account.totp_pending_secret
    account.totp_pending_secret = None
    account.totp_enabled = True
    session.commit()
    return {"ok": True}


@router.post("/totp/disable", dependencies=[Depends(require_user)])
def disable_totp(
    body: TotpDisableIn,
    username: str = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    account = _current(session, username)
    if not account.totp_enabled or account.totp_secret is None:
        raise HTTPException(status_code=409, detail="两步验证没有开启")
    if not verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="密码不正确")
    if not verify_code(account.totp_secret, body.code):
        raise HTTPException(status_code=401, detail="验证码不正确")
    account.totp_enabled = False
    account.totp_secret = None
    account.totp_pending_secret = None
    session.commit()
    return {"ok": True}
