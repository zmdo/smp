import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from smp_web.mcp_server import handle
from smpcore.models import Base, McpSettings, Server, ServerContainer, VirtualCard, Wallet, WalletAccount, WalletAddress


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(McpSettings(id=1, enabled=True, expose_servers=True, expose_wallets=True, expose_cards=True))
    server = Server(
        name="home",
        intranet_host="10.0.0.8",
        ssh_port=22,
        ssh_user="root",
        auth_method="password",
        secret_ciphertext="ssh-secret",
        reachability="online",
    )
    session.add(server)
    session.flush()
    session.add(
        ServerContainer(
            server_id=server.id,
            container_id="abc",
            name="freqtrade",
            image="freqtrade:latest",
            status="running",
            ports="8080/tcp",
            observed_at=server.created_at,
        )
    )
    session.add(
        VirtualCard(
            name="daily",
            platform="Dupay",
            holder="Ada",
            expiry="03/28",
            last4="4242",
            number_ciphertext="pan-secret",
            cvv_ciphertext="cvv-secret",
            country="United States",
            region="California",
            city="San Jose",
            address1="1 Market",
            postal_code="95113",
        )
    )
    wallet = Wallet(name="main", ciphertext="mnemonic-secret", mnemonic_sha256="a" * 64, word_count=12)
    session.add(wallet)
    session.flush()
    account = WalletAccount(wallet_id=wallet.id, name="Account 1", derivation_index=0)
    session.add(account)
    session.flush()
    session.add(
        WalletAddress(
            wallet_id=wallet.id,
            account_id=account.id,
            chain="ethereum",
            address="0xabc",
            derivation_path="m/44'/60'/0'/0/0",
            source="derived",
        )
    )
    session.commit()
    return session


def _call(session, method, params=None, request_id=1):
    row = session.get(McpSettings, 1)
    status, body = handle(session, {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}, row)
    assert status == 200
    return body["result"]


def test_initialize_and_hidden_tools():
    session = _session()
    result = _call(session, "initialize", {"protocolVersion": "2025-03-26"})
    assert result["serverInfo"]["name"] == "策略控制台"
    assert result["protocolVersion"] == "2025-03-26"
    names = {tool["name"] for tool in _call(session, "tools/list")["tools"]}
    assert names == {"list_servers", "list_containers", "list_wallets", "list_cards"}
    row = session.get(McpSettings, 1)
    row.expose_cards = False
    row.expose_wallets = False
    session.commit()
    names = {tool["name"] for tool in _call(session, "tools/list")["tools"]}
    assert names == {"list_servers", "list_containers"}


def test_tools_omit_secrets():
    session = _session()
    servers = json.loads(_call(session, "tools/call", {"name": "list_servers"})["content"][0]["text"])
    assert servers == [
        {
            "name": "home",
            "address": "10.0.0.8",
            "ssh_port": 22,
            "ssh_user": "root",
            "reachability": "online",
            "docker_version": None,
        }
    ]
    containers = json.loads(
        _call(session, "tools/call", {"name": "list_containers", "arguments": {"server": "home"}})["content"][0]["text"]
    )
    assert containers["containers"][0]["name"] == "freqtrade"
    cards = json.loads(_call(session, "tools/call", {"name": "list_cards"})["content"][0]["text"])
    assert cards[0]["last4"] == "4242"
    assert "pan-secret" not in json.dumps(cards)
    assert "cvv-secret" not in json.dumps(cards)
    wallets = json.loads(_call(session, "tools/call", {"name": "list_wallets"})["content"][0]["text"])
    assert wallets[0]["accounts"][0]["addresses"][0]["address"] == "0xabc"
    assert "mnemonic-secret" not in json.dumps(wallets)


def test_unknown_server_is_a_tool_error():
    session = _session()
    result = _call(session, "tools/call", {"name": "list_containers", "arguments": {"server": "missing"}})
    assert result["isError"] is True


def test_notification_has_no_body():
    session = _session()
    row = session.get(McpSettings, 1)
    status, body = handle(session, {"jsonrpc": "2.0", "method": "notifications/initialized"}, row)
    assert status == 202
    assert body is None
