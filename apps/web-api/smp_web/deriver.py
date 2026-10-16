"""Run the address deriver. The mnemonic is passed on stdin, never as an argument."""

from __future__ import annotations

import json
import os
import subprocess
import unicodedata
from pathlib import Path

from smp_web.config import settings


class DeriverError(Exception):
    pass


_ALLOWED = {"助记词不正确", "只接受 12 或 24 个单词", "请求无效"}


def normalize_mnemonic(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", value).lower().split())


def script_path() -> Path:
    configured = settings.wallet_deriver_script.strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "wallet-deriver" / "derive.mjs"


def derive(*, mnemonic: str | None = None, generate: bool = False, indices: list[int] | None = None) -> dict:
    payload: dict = {"indices": [0] if indices is None else indices}
    if generate:
        payload["generate"] = True
    else:
        payload["mnemonic"] = mnemonic
    path = script_path()
    if not path.is_file():
        raise DeriverError("地址派生不可用")
    try:
        completed = subprocess.run(
            [settings.wallet_deriver_node, str(path)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=20,
            check=False,
            env={**os.environ, "NODE_NO_WARNINGS": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeriverError("地址派生不可用") from exc
    try:
        body = json.loads(completed.stdout.decode() or "{}")
    except json.JSONDecodeError as exc:
        raise DeriverError("地址派生失败") from exc
    if completed.returncode != 0:
        message = body.get("error") if isinstance(body, dict) else None
        raise DeriverError(message if message in _ALLOWED else "地址派生失败")
    if not isinstance(body, dict) or not isinstance(body.get("accounts"), list):
        raise DeriverError("地址派生失败")
    return body
