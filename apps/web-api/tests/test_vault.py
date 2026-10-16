from smp_web.vault import VaultError, decrypt_mnemonic, encrypt_mnemonic


def test_round_trip_and_unique_nonce():
    phrase = "alpha beta gamma delta"
    first = encrypt_mnemonic("changeme", phrase)
    second = encrypt_mnemonic("changeme", phrase)
    assert first != second
    assert '"nonce":"' in first and first.split('"nonce":"')[1].split('"')[0] != second.split('"nonce":"')[1].split('"')[0]
    assert decrypt_mnemonic("changeme", first) == phrase


def test_wrong_password_does_not_open_the_vault():
    ciphertext = encrypt_mnemonic("changeme", "alpha beta gamma delta")
    try:
        decrypt_mnemonic("wrong-password", ciphertext)
    except VaultError:
        return
    raise AssertionError("wrong password opened the vault")
