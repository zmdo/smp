"""Copy a component script to the server, then run that file."""

from __future__ import annotations

from dataclasses import dataclass

import paramiko

from smp_ops.ssh import CommandResult, OpsSSHError, run_command
from smpcore.components import Component, load_catalog

_REMOTE_DIR = "/tmp/smp-components"


@dataclass(frozen=True)
class InstallReport:
    notes: list[str]
    changed: bool


def detect_components(client: paramiko.SSHClient) -> dict[str, dict[str, object]]:
    status: dict[str, dict[str, object]] = {}
    for component in load_catalog():
        result = _run_script(client, component.detect_script.read_bytes(), f"{component.id}-detect.sh", timeout=30)
        detail = ""
        if result.code == 0:
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            detail = lines[0][:120] if lines else ""
        status[component.id] = {"installed": result.code == 0, "detail": detail}
    return status


def install_missing(client: paramiko.SSHClient, component_ids: list[str]) -> InstallReport:
    wanted = set(component_ids)
    notes: list[str] = []
    changed = False
    for component in load_catalog():
        if component.id not in wanted:
            continue
        detected = _run_script(client, component.detect_script.read_bytes(), f"{component.id}-detect.sh", timeout=30)
        if detected.code == 0:
            notes.append(f"{component.name} 已安装，跳过")
            continue
        installed = _run_script(
            client, component.install_script.read_bytes(), f"{component.id}-install.sh", timeout=600
        )
        if installed.code != 0:
            detail = (installed.stderr or installed.stdout).strip()
            tail = detail[-500:] if detail else f"退出码 {installed.code}"
            raise OpsSSHError(f"{component.name} 安装失败：{tail}")
        notes.append(f"已安装 {component.name}")
        changed = True
    return InstallReport(notes=notes, changed=changed)


def _run_script(client: paramiko.SSHClient, script: bytes, remote_name: str, timeout: int) -> CommandResult:
    payload = script.replace(b"\r\n", b"\n")
    remote = f"{_REMOTE_DIR}/{remote_name}"
    try:
        sftp = client.open_sftp()
        try:
            try:
                sftp.stat(_REMOTE_DIR)
            except OSError:
                sftp.mkdir(_REMOTE_DIR)
            with sftp.file(remote, "wb") as handle:
                handle.write(payload)
            sftp.chmod(remote, 0o700)
        finally:
            sftp.close()
    except OSError as exc:
        raise OpsSSHError(f"无法把安装脚本传到服务器：{exc}") from exc
    return run_command(client, f"sh {remote}", timeout=timeout)
