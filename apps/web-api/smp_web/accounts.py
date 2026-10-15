"""Console accounts. The first start creates the admin from the environment."""

from __future__ import annotations

import bcrypt
from sqlalchemy import func, select

from smp_web.config import settings
from smp_web.deps import SessionLocal
from smpcore.models import Account


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def ensure_default_account() -> None:
    with SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(Account))
        if count:
            return
        session.add(
            Account(
                username=settings.admin_username.strip() or "admin",
                password_hash=hash_password(settings.admin_password),
                totp_enabled=False,
            )
        )
        session.commit()
