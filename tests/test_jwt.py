"""Unit tests for JWT generation and password hashing."""
import pytest

from ragbench.core.jwt import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    pwd = "securepassword123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert "$" in hashed
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_token_roundtrip():
    payload = {"sub": "user_abc", "email": "dev@ragbench.io", "workspace_id": "ws_123"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    decoded = decode_access_token(token)
    assert decoded["sub"] == "user_abc"
    assert decoded["email"] == "dev@ragbench.io"
    assert decoded["workspace_id"] == "ws_123"
    assert "exp" in decoded


def test_jwt_tampered_token_fails():
    token = create_access_token({"sub": "valid"})
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.badsignature"
    with pytest.raises(ValueError, match="Signature verification failed"):
        decode_access_token(tampered)
