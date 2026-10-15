"""Run the console on Windows itself.

Docker in WSL publishes port 8080 inside the virtual machine. On this machine
that port disappears whenever WSL restarts, so the browser on Windows cannot
open it. This process listens on 127.0.0.1:8080 directly.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "web-api"))
sys.path.insert(0, str(ROOT / "packages" / "smpcore"))

DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
database = DATA / "local.sqlite3"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{database.as_posix()}")
os.environ.setdefault("OPS_URL", "http://127.0.0.1:8081")
os.environ.setdefault("INTERNAL_TOKEN", "dev-internal-token")
os.environ.setdefault("SESSION_SECRET", "dev-session-secret-change-me")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "changeme")

from fastapi.responses import FileResponse  # noqa: E402
from smpcore.models import Base  # noqa: E402
from smp_web.deps import engine  # noqa: E402
from smp_web.main import app  # noqa: E402

Base.metadata.create_all(engine)

DIST = (ROOT / "apps" / "web-ui" / "dist").resolve()


def _page(full_path: str) -> FileResponse:
    candidate = (DIST / full_path).resolve() if full_path else DIST / "index.html"
    if candidate.is_file() and os.path.commonpath((candidate, DIST)) == str(DIST):
        return FileResponse(candidate)
    return FileResponse(DIST / "index.html")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return _page("")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str) -> FileResponse:
    return _page(full_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
