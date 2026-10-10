"""BYOK API Key encryption and decryption using AES-256 / Fernet."""
from cryptography.fernet import Fernet

from ragbench.core.config import settings


def get_cipher_suite() -> Fernet:
    """Instantiate Fernet cipher suite from configured application secret."""
    key = settings.effective_encryption_key or "default-dev-test-encryption-key"
    if len(key) != 44:
        import base64
        key = base64.urlsafe_b64encode(key.encode().ljust(32)[:32]).decode()
    return Fernet(key.encode())


def encrypt_api_key(raw_key: str) -> str:
    """Encrypt plain text API key prior to persistent database storage."""
    if not raw_key:
        raise ValueError("API key cannot be empty")
    cipher = get_cipher_suite()
    encrypted_bytes = cipher.encrypt(raw_key.encode())
    return encrypted_bytes.decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt stored API key for in-memory LLM provider instantiation."""
    if not encrypted_key:
        raise ValueError("Encrypted key cannot be empty")
    cipher = get_cipher_suite()
    decrypted_bytes = cipher.decrypt(encrypted_key.encode())
    return decrypted_bytes.decode()
