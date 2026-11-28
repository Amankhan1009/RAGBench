"""REST API Endpoints for Automated PII Masking, Reversible Rehydration, and Leakage Auditing."""
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from ragbench.api.v1.auth import get_current_workspace
from ragbench.models.workspace import Workspace
from ragbench.providers.webhook import WebhookProvider
from ragbench.sanitizer.engine import pii_sanitizer
from ragbench.sanitizer.schemas import (
    PIIEntityMatch,
    PIILeakageCheckRequest,
    PIILeakageCheckResult,
    PIIPresetScenario,
    PIIRestoreRequest,
    PIIRestoreResult,
    PIISanitizationResult,
    PIISanitizerConfig,
)

router = APIRouter(prefix="/sanitizer", tags=["PII Masking & Privacy Sanitizer"])


class MaskTextRequest(BaseModel):
    text: str = Field(min_length=1, description="Raw text containing confidential data to mask")
    config: Optional[PIISanitizerConfig] = Field(default=None, description="Custom detection preferences")


class DetectTextRequest(BaseModel):
    text: str = Field(min_length=1, description="Text to scan for sensitive PII entities")
    config: Optional[PIISanitizerConfig] = Field(default=None, description="Custom detection preferences")


@router.post(
    "/mask",
    response_model=PIISanitizationResult,
    status_code=status.HTTP_200_OK,
    summary="Sanitize and Mask Confidential PII in Text",
    description="Replaces sensitive SSNs, emails, credit cards, phones, and API keys with reversible tokens or redactions.",
)
async def mask_text(
    payload: MaskTextRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Sanitize confidential PII entities from text."""
    return pii_sanitizer.sanitize(payload.text, payload.config)


@router.post(
    "/unmask",
    response_model=PIIRestoreResult,
    status_code=status.HTTP_200_OK,
    summary="Reversibly Rehydrate Tokens to Original Values",
    description="Restores token placeholders back to original sensitive values upon delivery to authorized callers.",
)
async def unmask_text(
    payload: PIIRestoreRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Rehydrate tokens into original confidential text."""
    return pii_sanitizer.restore(payload.sanitized_text, payload.token_map)


@router.post(
    "/detect",
    response_model=List[PIIEntityMatch],
    status_code=status.HTTP_200_OK,
    summary="Detect PII Entities Without Modification",
    description="Locates character spans of sensitive personal data with confidence scores.",
)
async def detect_pii(
    payload: DetectTextRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Scan and return entity spans without rewriting text."""
    return pii_sanitizer.detect_entities(payload.text, payload.config)


@router.post(
    "/evaluate-leakage",
    response_model=PIILeakageCheckResult,
    status_code=status.HTTP_200_OK,
    summary="Audit RAG Generation for Context PII Leakage",
    description="Evaluates whether confidential PII present in retrieved context passages leaked unmasked into model generation.",
)
async def evaluate_leakage(
    payload: PIILeakageCheckRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Evaluate context PII leakage into output."""
    return pii_sanitizer.evaluate_leakage(payload.context_chunks, payload.generated_text)


@router.get(
    "/presets",
    response_model=List[PIIPresetScenario],
    status_code=status.HTTP_200_OK,
    summary="Get PII Preset Scenarios",
    description="Retrieve pre-configured sample datasets for testing masking, restoration, and leakage auditing.",
)
async def get_pii_presets():
    """Return preset PII testing scenarios."""
    return pii_sanitizer.get_presets()


class SanitizerWebhookProbeRequest(BaseModel):
    webhook_url: str = Field(..., min_length=1, description="Custom HTTP/HTTPS RAG endpoint URL")
    text: str = Field(..., min_length=1, description="Raw prompt containing PII to mask before sending to webhook")
    api_key: Optional[str] = Field(default=None, description="Optional Bearer token for webhook")
    config: Optional[PIISanitizerConfig] = Field(default=None, description="Custom PII masking preferences")


class SanitizerWebhookProbeResponse(BaseModel):
    sanitization: PIISanitizationResult
    webhook_response: str
    latency_ms: float
    leakage_check: PIILeakageCheckResult
    rehydrated_response: str


@router.post(
    "/probe-webhook",
    response_model=SanitizerWebhookProbeResponse,
    status_code=status.HTTP_200_OK,
    summary="Mask PII, Forward to Live Custom Webhook, and Audit Response",
    description="Sanitizes sensitive PII before sending to a custom webhook URL, checks the live response for PII leakage, and rehydrates tokens.",
)
async def probe_webhook_with_sanitizer(
    payload: SanitizerWebhookProbeRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """End-to-end zero-leakage PII sanitization & auditing against a live webhook."""
    from fastapi import HTTPException

    sanitized = pii_sanitizer.sanitize(payload.text, payload.config)
    try:
        provider = WebhookProvider(
            webhook_url=payload.webhook_url.strip(),
            api_key=payload.api_key or "",
        )
        gen_res = await provider.generate(sanitized.sanitized_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook call failed: {str(exc)}")

    leakage_check = pii_sanitizer.check_rag_leakage(
        context=payload.text,
        response=gen_res.generated_text,
    )
    rehydrated_text = gen_res.generated_text
    if sanitized.token_map:
        restored = pii_sanitizer.restore(gen_res.generated_text, sanitized.token_map)
        rehydrated_text = restored.restored_text

    return SanitizerWebhookProbeResponse(
        sanitization=sanitized,
        webhook_response=gen_res.generated_text,
        latency_ms=round(gen_res.latency_ms, 2),
        leakage_check=leakage_check,
        rehydrated_response=rehydrated_text,
    )
