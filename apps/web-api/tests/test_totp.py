from urllib.parse import unquote

import pyotp

from smp_web.totp import new_secret, provisioning_uri, verify_code


def test_accepts_current_code_and_rejects_garbage():
    secret = new_secret()
    assert verify_code(secret, pyotp.TOTP(secret).now())
    assert verify_code(secret, "000000") is False
    uri = unquote(provisioning_uri(secret, "admin"))
    assert "策略控制台" in uri
    assert secret in uri
