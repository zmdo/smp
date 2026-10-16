from smpcore.components import load_catalog, normalize_selection
from smpcore.ensure import ensure_runtime_schema
from smp_web.region import chosen_region, format_place, lookup_region
from sqlalchemy import create_engine, inspect, text


def test_catalog_reads_script_files():
    catalog = {item.id: item for item in load_catalog()}
    assert set(catalog) == {"docker", "compose"}
    assert catalog["compose"].requires == ("docker",)
    for item in catalog.values():
        install = item.install_script.read_text(encoding="utf-8")
        assert item.detect_script.is_file()
        assert "sudo" in install
        assert "apt-get" in install


def test_compose_requires_docker():
    try:
        normalize_selection(["compose"])
    except ValueError as exc:
        assert "Docker Engine" in str(exc)
    else:
        raise AssertionError("compose alone should be rejected")
    assert normalize_selection(["compose", "docker"]) == ["docker", "compose"]


def test_place_drops_repeated_names():
    assert format_place("中国", "香港", "香港") == "中国 香港"


def test_private_address_is_intranet():
    assert lookup_region("10.0.0.8") == "内网"
    assert lookup_region("192.168.1.9") == "内网"


def test_public_address_uses_lookup():
    def fetch(ip: str) -> dict:
        assert ip == "43.128.69.189"
        return {"status": "success", "country": "中国", "regionName": "香港", "city": "香港"}

    assert lookup_region("43.128.69.189", fetch=fetch) == "中国 香港"


def test_written_region_is_kept():
    assert chosen_region("10.0.0.8", "  机房 A ") == "机房 A"


def test_blank_region_uses_intranet_or_lookup():
    assert chosen_region("10.0.0.8", "  ") == "内网"

    def fetch(ip: str) -> dict:
        assert ip == "43.128.69.189"
        return {"status": "success", "country": "新加坡", "regionName": "", "city": "新加坡"}

    assert chosen_region("43.128.69.189", None, fetch=fetch, resolve=lambda host: host) == "新加坡"


def test_sqlite_accepts_install_job_action():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE servers (id TEXT PRIMARY KEY)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE ops_jobs ("
                "id TEXT PRIMARY KEY, action TEXT NOT NULL, "
                "CONSTRAINT ck_ops_jobs_action CHECK (action IN ('test_connection', 'inspect'))"
                ")"
            )
        )
    ensure_runtime_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO ops_jobs (id, action) VALUES ('job', 'install_components')"))
        names = {row[1] for row in connection.execute(text("PRAGMA table_info(servers)"))}
    assert {"region", "auto_install", "install_component_ids", "component_status", "group_id"} <= names
    assert "server_groups" in set(inspect(engine).get_table_names())
