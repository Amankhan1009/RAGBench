"""Pydantic schemas for the Automated PII Masking & Data Sanitization Pipeline."""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PIIEntityType(str, Enum):
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    API_KEY = "api_key"
    IP_ADDRESS = "ip_address"


class MaskingStrategy(str, Enum):
    TOKEN = "token"  # Reversible token: [EMAIL_1], [SSN_1]
    REDACT = "redact"  # Generic replacement: [REDACTED_EMAIL]
    HASH = "hash"  # Deterministic SHA-256 hash prefix: [HASH_e3b0c4]


class PIIEntityMatch(BaseModel):
    """Represents a single detected PII entity in text."""
    entity_type: PIIEntityType = Field(description="Detected PII classification")
    text: str = Field(description="Original confidential text snippet")
    start: int = Field(description="Starting character offset in source text")
    end: int = Field(description="Ending character offset in source text")
    replacement: str = Field(description="Masking replacement token")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence score")


class PIISanitizerConfig(BaseModel):
    """Configuration options for PII detection and redaction."""
    strategy: MaskingStrategy = Field(default=MaskingStrategy.TOKEN, description="Redaction format")
    mask_email: bool = Field(default=True, description="Detect and mask email addresses")
    mask_phone: bool = Field(default=True, description="Detect and mask phone numbers")
    mask_ssn: bool = Field(default=True, description="Detect and mask Social Security Numbers")
    mask_credit_card: bool = Field(default=True, description="Detect and mask Credit Card numbers with Luhn check")
    mask_api_key: bool = Field(default=True, description="Detect and mask API keys and secrets")
    mask_ip_address: bool = Field(default=True, description="Detect and mask IPv4/IPv6 addresses")


class PIISanitizationResult(BaseModel):
    """Detailed result of PII detection and redaction."""
    original_text: str = Field(description="Raw source text before sanitization")
    sanitized_text: str = Field(description="Sanitized text safe for transmission")
    entities_found: List[PIIEntityMatch] = Field(default_factory=list, description="All detected PII occurrences")
    entities_count: Dict[str, int] = Field(default_factory=dict, description="Count of occurrences per PII type")
    token_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Reversible mapping from replacement token to original confidential snippet"
    )
    latency_ms: float = Field(default=0.0, description="Sanitization execution duration in milliseconds")


class PIIRestoreRequest(BaseModel):
    """Payload to reverse tokens and restore original PII."""
    sanitized_text: str = Field(min_length=1, description="Text containing replacement tokens")
    token_map: Dict[str, str] = Field(description="Token map generated during sanitization")


class PIIRestoreResult(BaseModel):
    """Result of restoring sanitized tokens back into original values."""
    restored_text: str = Field(description="Text with original confidential data re-injected")
    tokens_restored_count: int = Field(default=0, description="Number of tokens rehydrated")
    latency_ms: float = Field(default=0.0, description="Restoration duration in milliseconds")


class PIILeakageCheckRequest(BaseModel):
    """Payload to evaluate if private context passages leaked into model generation."""
    context_chunks: List[str] = Field(min_length=1, description="Retrieved passages potentially holding confidential data")
    generated_text: str = Field(min_length=1, description="Generated model response to audit for leakage")


class PIILeakageCheckResult(BaseModel):
    """Diagnostic audit result checking if private context data leaked into generated text."""
    leaked: bool = Field(description="Whether any confidential context PII was exposed in the response")
    leakage_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of leaked entities (0.0 safe, 1.0 full leak)")
    leaked_entities: List[PIIEntityMatch] = Field(default_factory=list, description="Specific entities from context found unmasked in output")
    total_context_pii_count: int = Field(default=0, description="Total PII items found in context")
    total_leaked_count: int = Field(default=0, description="Number of private items leaked unmasked into output")
    reason: str = Field(default="No confidential data leaked", description="Diagnostic explanation")
    latency_ms: float = Field(default=0.0, description="Audit evaluation time in milliseconds")


class PIIPresetScenario(BaseModel):
    """Sample adversarial or enterprise scenario for testing PII redaction."""
    id: str
    title: str
    description: str
    sample_text: str
    sample_context: Optional[str] = None
    expected_entities: List[str]
