"""Pydantic schemas for AI Red-Teaming, Adversarial Fuzzing, and Security Posture Scoring."""
import uuid
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AttackCategory(str, Enum):
    DIRECT_INJECTION = "direct_injection"
    JAILBREAK = "jailbreak"
    INDIRECT_INJECTION = "indirect_injection"
    SYSTEM_EXTRACTION = "system_extraction"
    TOPICAL_EVASION = "topical_evasion"
    PII_LEAKAGE = "pii_leakage"


class AttackSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackResultStatus(str, Enum):
    DEFENDED = "defended"
    BREACHED = "breached"
    ERROR = "error"


class AttackTestCase(BaseModel):
    """Definition of a single adversarial attack test case."""
    id: str
    category: AttackCategory
    severity: AttackSeverity
    name: str
    description: str
    prompt: str
    context_passage: Optional[str] = None
    breach_indicator_patterns: List[str] = Field(
        default_factory=list,
        description="Phrases indicating the model fell victim to the adversarial attack"
    )
    refusal_indicator_patterns: List[str] = Field(
        default_factory=list,
        description="Standard refusal indicators confirming model defended the attack"
    )
    mitigation_recommendation: str = Field(
        description="Actionable remediation guidance if this attack breaches the target"
    )


class AttackExecutionResult(BaseModel):
    """Diagnostic outcome of executing an adversarial attack against a target model."""
    test_case: AttackTestCase
    status: AttackResultStatus
    model_output: str
    latency_ms: float
    cost_usd: float = 0.0
    guardrails_intercepted: bool = False
    breach_reason: Optional[str] = None
    mitigation_recommendation: str


class RedTeamBenchmarkRequest(BaseModel):
    """Payload to initiate an automated adversarial red-team benchmark."""
    provider: str = Field(default="mock", description="Target provider: 'groq', 'google', 'openai', 'webhook', 'mock'")
    model: str = Field(default="openai/gpt-oss-120b", description="Model identifier to evaluate")
    api_key: Optional[str] = Field(default=None, description="Optional BYOK API key")
    categories: Optional[List[AttackCategory]] = Field(
        default=None,
        description="Specific attack categories to run (runs all 6 if omitted)"
    )
    guardrails_enabled: bool = Field(default=True, description="Enable RAGBench NeMo guardrails during testing")
    pii_sanitization_enabled: bool = Field(default=True, description="Enable PII masking pipeline during testing")


class RedTeamBenchmarkReport(BaseModel):
    """Executive security posture benchmark report."""
    benchmark_id: str = Field(default_factory=lambda: f"redteam-{uuid.uuid4().hex[:10]}")
    target_provider: str
    target_model: str
    total_attacks: int
    defended_attacks: int
    breached_attacks: int
    security_posture_score: float = Field(description="Percentage of attacks successfully defended (0.0 to 100.0%)")
    risk_grade: str = Field(description="Letter grade: 'A+', 'A', 'B', 'C', 'F'")
    defense_rate_by_category: Dict[str, float] = Field(description="Defense rate percentage per attack category")
    critical_vulnerabilities_count: int = Field(default=0)
    guardrails_intercepted_count: int = Field(default=0)
    attack_results: List[AttackExecutionResult]
    executive_summary: str
    created_at: str
    latency_ms: float
