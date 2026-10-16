from smp_ops.metrics import parse_sample


def test_parse_sample_computes_usage():
    text = "2 1000 800 2000 1400 1024 512 1000 900"
    parsed = parse_sample(text)
    assert parsed["cpu_cores"] == 2
    assert parsed["cpu_percent"] == 40
    assert parsed["mem_total_bytes"] == 1024 * 1024
    assert parsed["mem_used_bytes"] == 512 * 1024
    assert parsed["disk_total_bytes"] == 1000
    assert parsed["disk_used_bytes"] == 900


def test_parse_sample_clamps_cpu_and_disk():
    text = "1 10 10 10 10 2048 4096 100 150"
    parsed = parse_sample(text)
    assert parsed["cpu_percent"] == 0
    assert parsed["mem_used_bytes"] == 0
    assert parsed["disk_used_bytes"] == 100
