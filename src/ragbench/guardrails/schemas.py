"""Pydantic schemas for NVIDIA NeMo-compatible Guardrails, Input/Output Rails, and Colang Flows."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RailType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    TOPICAL = "topical"


class RailAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REWRITE = "rewrite"
    FLAG = "flag"


class ViolationType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    SYSTEM_LEAK_ATTEMPT = "system_leak_attempt"
    OFF_TOPIC = "off_topic"
    HALLUCINATION = "hallucination"
    UNGROUNDED_CLAIM = "ungrounded_claim"
    TOXICITY = "toxicity"


class GuardrailCheckResult(BaseModel):
    """Diagnostic verdict produced by an input, topical, or output guardrail check."""
    passed: bool = Field(description="Whether the text passed all active security checks")
    action: RailAction = Field(default=RailAction.ALLOW, description="Enforced action: allow, block, rewrite, or flag")
    violations: List[str] = Field(default_factory=list, description="List of detected policy violations")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence score")
    sanitized_text: Optional[str] = Field(default=None, description="Sanitized or rewritten text if applicable")
    refusal_response: Optional[str] = Field(default=None, description="Safe polite refusal message if blocked")
    reason: str = Field(default="Passed all safety boundaries", description="Human-readable diagnostic explanation")
    execution_time_ms: float = Field(default=0.0, description="Guardrail inspection latency in milliseconds")


class InputRailRequest(BaseModel):
    """Payload to test prompt safety against input and jailbreak rails."""
    prompt: str = Field(min_length=1, description="Raw prompt text to inspect")
    check_jailbreaks: bool = Field(default=True, description="Enable jailbreak and adversarial persona blocking")
    check_prompt_injection: bool = Field(default=True, description="Enable instruction override and injection checks")
    check_system_leak: bool = Field(default=True, description="Enable system prompt extraction protection")


class OutputRailRequest(BaseModel):
    """Payload to test generated model output against retrieved RAG contexts."""
    response_text: str = Field(min_length=1, description="Model generated text to verify")
    retrieved_contexts: List[str] = Field(default_factory=list, description="Retrieved passages used as ground truth")
    hallucination_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum grounding threshold required to pass")


class TopicalRailConfig(BaseModel):
    """Colang-style topical boundary configuration."""
    domain_name: str = Field(default="Enterprise Knowledge & Operations", description="Allowed business domain name")
    allowed_topics: List[str] = Field(
        default=["product documentation", "company policy", "order tracking", "technical support", "billing"],
        description="Allowed topical domains"
    )
    disallowed_topics: List[str] = Field(
        default=["politics", "gaming cheats", "illegal weapons", "creative fiction", "gambling"],
        description="Explicitly blocked topical domains"
    )
    refusal_message: str = Field(
        default="I am specialized in enterprise support and cannot assist with topics outside this domain.",
        description="Approved polite refusal for off-topic queries"
    )


class WorkspaceGuardrailPolicy(BaseModel):
    """Workspace-scoped guardrail configuration."""
    workspace_id: str
    input_rails_enabled: bool = True
    jailbreak_blocker_enabled: bool = True
    system_prompt_protection: bool = True
    topical_rails_enabled: bool = False
    output_rails_enabled: bool = True
    hallucination_threshold: float = 0.5
    topical_config: TopicalRailConfig = Field(default_factory=TopicalRailConfig)


class GuardrailPresetScenario(BaseModel):
    """Preset attack or evaluation scenario for testing guardrails."""
    id: str
    name: str
    category: str
    description: str
    test_input: str
    contexts: Optional[List[str]] = None
    expected_violation: str
    expected_action: RailAction
