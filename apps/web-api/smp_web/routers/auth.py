from fastapi import APIRouter, Depends, HTTPException, Request, Response

from smp_web.deps import passwords, require_user
from smp_web.schemas import LoginIn, MeOut

router = APIRouter(prefix="/api/auth")


@router.post("/login")
def login(body: LoginIn, request: Request) -> dict[str, bool]:
    if not passwords.verify(body.password):
        raise HTTPException(status_code=401, detail="口令不正确")
    request.session["user"] = "admin"
    return {"ok": True}


@router.post("/logout")
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/me", response_model=MeOut)
def me(request: Request) -> MeOut:
    return MeOut(
        authenticated=request.session.get("user") == "admin",
        password_is_default=passwords.is_default,
    )


@router.get("/session", dependencies=[Depends(require_user)])
def session_ok() -> dict[str, bool]:
    return {"ok": True}
