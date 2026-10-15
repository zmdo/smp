from smp_ops.docker_parse import (
    docker_access_message,
    excerpt,
    parse_compose_version,
    parse_docker_version,
    parse_labels,
    parse_ps,
    scrub,
)


def test_parse_managed_container():
    raw = (
        '{"ID":"abc123","Names":"/smp-demo","Image":"freqtradeorg/freqtrade:stable",'
        '"State":"running","Ports":"10.0.0.8:8080->8080/tcp",'
        '"Labels":"smp.managed=true,smp.strategy=demo"}'
    )
    rows = parse_ps(raw)
    assert len(rows) == 1
    assert rows[0].name == "smp-demo"
    assert rows[0].status == "running"
    assert rows[0].managed is True
    assert rows[0].strategy_slug == "demo"


def test_parse_skips_blank_and_marks_unmanaged():
    raw = '\n{"ID":"abc","Names":"nginx","Image":"nginx:1.27","State":"exited","Labels":""}\n'
    rows = parse_ps(raw)
    assert rows[0].managed is False
    assert rows[0].strategy_slug is None
    assert rows[0].status == "exited"


def test_labels_split_on_first_equals():
    assert parse_labels("smp.managed=true,com.example=a=b")["com.example"] == "a=b"


def test_versions_and_scrub():
    assert parse_docker_version('{"Server":{"Version":"29.1.3"},"Client":{"Version":"29.1.3"}}') == "29.1.3"
    assert parse_compose_version('{"version":"2.40.0"}') == "2.40.0"
    assert scrub("password=s3cret-value", "s3cret-value") == "password=***"
    assert excerpt("abc", limit=2) == "…\nbc"


def test_docker_access_hints():
    assert "docker 组" in docker_access_message("permission denied while connecting to the docker socket")
    assert "没有 docker 命令" in docker_access_message("bash: docker: command not found")
