"""Unit tests for Multi-Tenant Workspace & BYOK Key schemas and models."""
from ragbench.core.security import decrypt_api_key, encrypt_api_key
from ragbench.models.workspace import Workspace, WorkspaceApiKey
from ragbench.schemas.auth import ApiKeyMetadata, ApiKeyRegister, WorkspaceCreate, WorkspaceResponse


def test_workspace_schemas():
    create_req = WorkspaceCreate(name="Acme Corp AI")
    assert create_req.name == "Acme Corp AI"

    ws_res = WorkspaceResponse(
        id="ws-123",
        name="Acme Corp AI",
        api_key="rb_ws_testkey1234567890",
    )
    assert ws_res.id == "ws-123"
    assert ws_res.api_key.startswith("rb_ws_")


def test_byok_encryption_and_preview_isolation():
    plain_key = "gsk_live_secret_key_1234567890"
    encrypted = encrypt_api_key(plain_key)

    key_record = WorkspaceApiKey(
        workspace_id="ws-123",
        provider="groq",
        encrypted_key=encrypted,
    )
    assert key_record.encrypted_key != plain_key
    assert decrypt_api_key(key_record.encrypted_key) == plain_key

    # Preview metadata must never leak the full key
    meta = ApiKeyMetadata(
        id="key-1",
        provider="groq",
        key_preview=f"{plain_key[:6]}...{plain_key[-4:]}",
    )
    assert meta.key_preview == "gsk_li...7890"
    assert plain_key not in meta.model_dump_json()
