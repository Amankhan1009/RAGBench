"""REST API Endpoints for Automated PII Masking, Reversible Rehydration, and Leakage Auditing."""
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from ragbench.api.v1.auth import get_current_workspace
from ragbench.models.workspace import Workspace
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
