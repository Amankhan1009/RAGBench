"""Unit tests for BYOK AES-256 Fernet API key encryption."""
import pytest
from cryptography.fernet import InvalidToken

from ragbench.core.security import decrypt_api_key, encrypt_api_key


def test_byok_encryption_roundtrip():
    raw_key = "gsk_test_api_key_1234567890abcdef"
    encrypted = encrypt_api_key(raw_key)

    assert encrypted != raw_key
    assert isinstance(encrypted, str)

    decrypted = decrypt_api_key(encrypted)
    assert decrypted == raw_key


def test_byok_invalid_token_fails():
    with pytest.raises(InvalidToken):
        decrypt_api_key("invalid_corrupted_ciphertext")
