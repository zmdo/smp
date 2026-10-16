from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from smp_web.accounts import ensure_default_account
from smp_web.routers.cards import ensure_virtual_card_columns
from smp_web.config import settings
from smp_web.deps import SessionLocal
from smp_web.routers import auth, cards, jobs, keys, servers, wallets


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_default_account()
    ensure_virtual_card_columns()
    yield


app = FastAPI(title="策略控制台", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="smp_session",
    max_age=14 * 24 * 3600,
    same_site="lax",
    https_only=False,
)
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(keys.router)
app.include_router(cards.router)
app.include_router(wallets.router)
app.include_router(jobs.router)


@app.middleware("http")
async def no_store_api(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health() -> dict[str, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="数据库不可用") from exc
    return {"status": "ok"}
