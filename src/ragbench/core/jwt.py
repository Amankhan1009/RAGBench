"""JWT token generation and secure password hashing with zero external dependencies."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict

JWT_SECRET = os.getenv("RAGBENCH_JWT_SECRET", "ragbench-jwt-production-secret-key-32b")
JWT_EXPIRATION_SECONDS = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored salt and PBKDF2 hash in constant time."""
    try:
        salt, expected_key = hashed.split("$", 1)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return hmac.compare_digest(key.hex(), expected_key)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(data: Dict[str, Any]) -> str:
    """Generate an RFC 7519 compliant HS256 JWT access token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    now = int(time.time())
    payload["iat"] = now
    payload["exp"] = now + JWT_EXPIRATION_SECONDS

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and cryptographically verify an HS256 JWT access token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token structure")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_decode(sig_b64), expected_sig):
        raise ValueError("Signature verification failed")

    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    if payload.get("exp", 0) < time.time():
        raise ValueError("Token has expired")
    return payload
