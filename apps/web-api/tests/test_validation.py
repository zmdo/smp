import pytest

from smp_web.validation import FieldError, clean_host, clean_name, clean_user


def test_accepts_intranet_host_and_user():
    assert clean_host(" 10.0.0.8 ") == "10.0.0.8"
    assert clean_host("203.0.113.10") == "203.0.113.10"
    assert clean_host("[2001:db8::1]") == "2001:db8::1"
    assert clean_user("trader") == "trader"
    assert clean_name(" 机房甲 ") == "机房甲"


def test_rejects_hostname_and_shell_metacharacters():
    with pytest.raises(FieldError):
        clean_host("trade.example.com")
    with pytest.raises(FieldError):
        clean_host("10.0.0.8;reboot")
    with pytest.raises(FieldError):
        clean_user("root && id")
