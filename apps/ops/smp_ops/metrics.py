"""Sample CPU, memory, and disk on each registered server once a second."""

from __future__ import annotations

import logging
import threading
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from smp_ops.crypto import decrypt
from smp_ops.ssh import connect, run_command
from smp_ops.worker import _ciphertext
from smpcore.models import Server, utcnow

log = logging.getLogger("smp.ops.metrics")

SAMPLE_SCRIPT = r"""
cores=$(nproc 2>/dev/null || grep -c '^processor' /proc/cpuinfo)
read_cpu() { awk '/^cpu /{idle=$5+$6; t=0; for(i=2;i<=NF;i++) t+=$i; print t, idle}' /proc/stat; }
a=$(read_cpu)
sleep 1
b=$(read_cpu)
mem_total=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
mem_avail=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
disk_total=$(df -B1 -P / | awk 'NR==2 {print $2}')
disk_used=$(df -B1 -P / | awk 'NR==2 {print $3}')
printf '%s %s %s %s %s %s %s\n' "$cores" "$a" "$b" "$mem_total" "$mem_avail" "$disk_total" "$disk_used"
"""


def parse_sample(text: str) -> dict[str, int]:
    parts = text.split()
    if len(parts) != 9:
        raise ValueError("采集结果无法解析")
    cores, a_total, a_idle, b_total, b_idle, mem_total_kb, mem_avail_kb, disk_total, disk_used = (
        int(part) for part in parts
    )
    if cores < 1 or mem_total_kb < 1 or disk_total < 1:
        raise ValueError("采集结果无法解析")
    delta = b_total - a_total
    idle = b_idle - a_idle
    if delta <= 0:
        cpu = 0
    else:
        cpu = round(100 * (delta - idle) / delta)
    mem_total = mem_total_kb * 1024
    mem_used = max(0, (mem_total_kb - mem_avail_kb) * 1024)
    return {
        "cpu_cores": cores,
        "cpu_percent": max(0, min(100, cpu)),
        "mem_total_bytes": mem_total,
        "mem_used_bytes": min(mem_used, mem_total),
        "disk_total_bytes": disk_total,
        "disk_used_bytes": max(0, min(disk_used, disk_total)),
    }


def metrics_loop(stop: threading.Event, sessions: sessionmaker[Session], fernet: Fernet) -> None:
    threads: dict[uuid.UUID, threading.Thread] = {}
    while not stop.is_set():
        try:
            with sessions() as session:
                ids = set(session.scalars(select(Server.id)).all())
        except Exception:
            log.exception("metric server list failed")
            stop.wait(5)
            continue
        for server_id in ids:
            thread = threads.get(server_id)
            if thread is None or not thread.is_alive():
                thread = threading.Thread(
                    target=_watch_server,
                    args=(stop, sessions, fernet, server_id),
                    name=f"ops-metrics-{server_id}",
                    daemon=True,
                )
                threads[server_id] = thread
                thread.start()
        stop.wait(5)


def _watch_server(
    stop: threading.Event,
    sessions: sessionmaker[Session],
    fernet: Fernet,
    server_id: uuid.UUID,
) -> None:
    while not stop.is_set():
        try:
            _sample_until_drop(stop, sessions, fernet, server_id)
        except Exception:
            log.warning("metric sample failed for %s", server_id)
        if stop.wait(3):
            return


def _sample_until_drop(
    stop: threading.Event,
    sessions: sessionmaker[Session],
    fernet: Fernet,
    server_id: uuid.UUID,
) -> None:
    with sessions() as session:
        server = session.get(Server, server_id)
        if server is None:
            return
        secret = decrypt(fernet, _ciphertext(session, server))
        host = server.intranet_host
        port = server.ssh_port
        username = server.ssh_user
        auth_method = server.auth_method
        expected = server.host_key_fingerprint
    client, _policy = connect(
        host=host,
        port=port,
        username=username,
        auth_method=auth_method,
        secret=secret,
        expected_fingerprint=expected,
    )
    try:
        while not stop.is_set():
            with sessions() as session:
                if session.get(Server, server_id) is None:
                    return
            result = run_command(client, SAMPLE_SCRIPT, timeout=8)
            if result.code != 0:
                raise RuntimeError((result.stderr or result.stdout or "采集失败").strip())
            values = parse_sample(result.stdout)
            values["metrics_at"] = utcnow()
            with sessions() as session:
                session.execute(update(Server).where(Server.id == server_id).values(**values))
                session.commit()
    finally:
        client.close()
