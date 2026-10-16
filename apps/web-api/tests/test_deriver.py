import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused")
os.environ.setdefault("INTERNAL_TOKEN", "unused")
os.environ.setdefault("SESSION_SECRET", "unused")
os.environ.setdefault("ADMIN_PASSWORD", "unused")

from smp_web.deriver import derive, normalize_mnemonic

METAMASK = "finish oppose decorate face calm tragic certain desk hour urge dinosaur mango"


def test_normalize_mnemonic_folds_case_and_whitespace():
    assert normalize_mnemonic("  Finish\nOPPOSE   decorate ") == "finish oppose decorate"


def test_import_matches_metamask_and_does_not_echo_the_mnemonic():
    result = derive(mnemonic=METAMASK, indices=[0, 1])
    assert "mnemonic" not in result
    assert result["word_count"] == 12
    first, second = result["accounts"]
    ethereum = {item["chain"]: item["address"] for item in first["addresses"]}
    assert ethereum["ethereum"].lower() == "0x1c96099350f13d558464ec79b9be4445aa0ef579"
    assert ethereum["ethereum"] == ethereum["bsc"] == ethereum["base"]
    second_eth = next(item["address"] for item in second["addresses"] if item["chain"] == "ethereum")
    assert second_eth.lower() == "0x1b00aed43a693f3a957f9feb5cc08afa031e37a0"
    assert ethereum["bitcoin"] == "bc1qrzx25ehct2va5tmr2kcrpk2p50edk2cm7kvq0a"
