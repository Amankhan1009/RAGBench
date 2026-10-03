"""Unit tests for BYOK API Key Encryption & Decryption."""
import pytest

from ragbench.core.security import decrypt_api_key, encrypt_api_key


def test_api_key_encryption_decryption():
    raw_key = "gsk_test_api_key_1234567890"
    encrypted = encrypt_api_key(raw_key)

    assert encrypted != raw_key
    assert len(encrypted) > 20

    decrypted = decrypt_api_key(encrypted)
    assert decrypted == raw_key


def test_empty_api_key_validation():
    with pytest.raises(ValueError):
        encrypt_api_key("")

    with pytest.raises(ValueError):
        decrypt_api_key("")
