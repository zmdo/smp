import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("INTERNAL_TOKEN", "unused")
os.environ.setdefault("SESSION_SECRET", "unused")
os.environ.setdefault("ADMIN_PASSWORD", "unused")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from smp_web.routers.servers import _bind_auth
from smp_web.schemas import ServerIn
from smpcore.models import Base, Server, SshKey


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _server() -> Server:
    return Server(
        name="sg",
        intranet_host="43.128.69.189",
        ssh_port=22,
        ssh_user="ubuntu",
        auth_method="private_key",
        secret_ciphertext="",
        reachability="unknown",
    )


def test_existing_key_is_attached_without_reencrypting(monkeypatch):
    monkeypatch.setattr(
        "smp_web.routers.servers.encrypt_secret",
        lambda plaintext, method: (_ for _ in ()).throw(AssertionError("should not encrypt")),
    )
    session = _session()
    key = SshKey(name="tencent", fingerprint="SHA256:hn9", secret_ciphertext="stored-key")
    session.add(key)
    session.flush()
    server = _server()
    session.add(server)
    changed = _bind_auth(
        session,
        server,
        ServerIn(
            name="sg",
            intranet_host="43.128.69.189",
            ssh_user="ubuntu",
            auth_method="private_key",
            ssh_key_id=key.id,
        ),
        creating=True,
    )
    assert changed is True
    assert server.ssh_key_id == key.id
    assert server.secret_ciphertext == ""


def test_pasted_key_is_stored_once_and_linked(monkeypatch):
    monkeypatch.setattr(
        "smp_web.key_store.encrypt_secret",
        lambda plaintext, method: ("cipher", "SHA256:hn9"),
    )
    session = _session()
    server = _server()
    session.add(server)
    _bind_auth(
        session,
        server,
        ServerIn(
            name="sg",
            intranet_host="43.128.69.189",
            ssh_user="ubuntu",
            auth_method="private_key",
            secret="-----BEGIN RSA PRIVATE KEY-----\nabc\n",
            ssh_key_name="腾讯云",
        ),
        creating=True,
    )
    session.flush()
    saved = session.get(SshKey, server.ssh_key_id)
    assert saved is not None
    assert saved.name == "腾讯云"
    assert saved.fingerprint == "SHA256:hn9"
    assert saved.secret_ciphertext == "cipher"


def test_password_ciphertext_is_the_encrypted_string(monkeypatch):
    monkeypatch.setattr(
        "smp_web.routers.servers.encrypt_secret",
        lambda plaintext, method: (f"enc:{plaintext}", None),
    )
    session = _session()
    server = _server()
    session.add(server)
    _bind_auth(
        session,
        server,
        ServerIn(
            name="sg",
            intranet_host="43.128.69.189",
            ssh_user="ubuntu",
            auth_method="password",
            secret="secret-pass",
        ),
        creating=True,
    )
    assert server.auth_method == "password"
    assert server.ssh_key_id is None
    assert server.secret_ciphertext == "enc:secret-pass"
