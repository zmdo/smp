import pytest

from smp_web.validation import FieldError, clean_card_number, clean_cvv, clean_expiry


def test_accepts_a_spaced_card_number():
    assert clean_card_number("4242 4242 4242 4242") == "4242424242424242"


def test_rejects_a_bad_card_number():
    with pytest.raises(FieldError):
        clean_card_number("4242424242424243")


def test_expiry_and_cvv():
    assert clean_expiry("03/28") == "03/28"
    assert clean_cvv("123") == "123"
    with pytest.raises(FieldError):
        clean_expiry("13/28")
