"""Engine for Automated PII Detection, Redaction, Reversible Rehydration, and Leakage Auditing."""
import hashlib
import re
import time
from typing import Dict, List, Optional, Tuple

from ragbench.core.logging import logger
from ragbench.sanitizer.schemas import (
    MaskingStrategy,
    PIIEntityMatch,
    PIIEntityType,
    PIILeakageCheckResult,
    PIIPresetScenario,
    PIIRestoreResult,
    PIISanitizationResult,
    PIISanitizerConfig,
)

# Regex Patterns for High-Speed Zero-Dependency PII Detection
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", re.IGNORECASE
)

SSN_PATTERN = re.compile(
    r"\b(?!000|666)\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b"
)

# Matches US and International E.164 phone formats
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)

# Matches standard Credit Card formatting (13 to 19 digits)
CANDIDATE_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[- ]?){3}\d{4}\b|\b\d{13,19}\b"
)

# Matches cloud API keys, access tokens, and secrets
OPENAI_KEY_PATTERN = re.compile(r"\bsk-[a-zA-Z0-9]{20,60}\b")
AWS_KEY_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
GITHUB_TOKEN_PATTERN = re.compile(r"\bgh[pousr]_[a-zA-Z0-9]{36,40}\b")
GENERIC_BEARER_PATTERN = re.compile(
    r"(?:api[_-]?key|secret|token|password)[\s:=]+['\"]?([a-zA-Z0-9_\-]{20,64})['\"]?",
    re.IGNORECASE
)

# Matches IPv4 addresses
IPV4_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
)


def _luhn_checksum(candidate: str) -> bool:
    """Validate card number using Luhn algorithm to prevent false positives on random 16-digit IDs."""
    digits = [int(c) for c in candidate if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for idx, d in enumerate(reverse_digits):
        if idx % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


PRESET_SCENARIOS: List[PIIPresetScenario] = [
    PIIPresetScenario(
        id="customer_support_billing",
        title="Customer Support Ticket (Billing & Contact)",
        description="Customer email containing credit card, phone number, and personal email address.",
        sample_text=(
            "Hello Support, my email is alice.smith@example.com and phone is +1-555-234-5678. "
            "Please process a refund to my Visa card 4532-0150-1234-5671 expiring 08/28."
        ),
        sample_context=(
            "Customer Account #9401: Alice Smith (alice.smith@example.com, +1-555-234-5678). "
            "Card on file: 4532-0150-1234-5671."
        ),
        expected_entities=["email", "phone_number", "credit_card"],
    ),
    PIIPresetScenario(
        id="hr_onboarding_record",
        title="HR Employee Onboarding Record (SSN & Identity)",
        description="Employee confidential intake record containing SSN, phone number, and corporate email.",
        sample_text=(
            "New hire John Doe (johndoe@acme-corp.org) submitted onboarding docs. "
            "SSN provided is 123-45-6789 and emergency phone is 415-555-8901."
        ),
        sample_context=(
            "Employee Master File: John Doe. SSN: 123-45-6789. Email: johndoe@acme-corp.org."
        ),
        expected_entities=["email", "ssn", "phone_number"],
    ),
    PIIPresetScenario(
        id="devops_secret_leak",
        title="Infrastructure Incident Log (API Keys & IP Addresses)",
        description="DevOps log dump inadvertently containing live AWS credentials, OpenAI keys, and server IPs.",
        sample_text=(
            "Database connection failed at host 192.168.1.105. "
            "Attempted auth using AWS key AKIAIOSFODNN7EXAMPLE and OpenAI secret sk-live9876543210abcdef12345678."
        ),
        sample_context=(
            "Internal cluster node 192.168.1.105 with root credential AKIAIOSFODNN7EXAMPLE."
        ),
        expected_entities=["ip_address", "api_key"],
    ),
    PIIPresetScenario(
        id="clean_rag_query",
        title="Clean Technical RAG Query (Zero PII)",
        description="Standard query with technical concepts and zero confidential PII entities.",
        sample_text="Explain the Pareto frontier trade-offs between LLM response quality, token latency, and inference cost.",
        sample_context="RAG systems balance latency and accuracy using multi-stage retrieval pipelines.",
        expected_entities=[],
    ),
]


class PIISanitizer:
    """Enterprise PII Sanitization, Masking, Reversible Rehydration, and Leakage Engine."""

    def detect_entities(
        self,
        text: str,
        config: Optional[PIISanitizerConfig] = None,
    ) -> List[PIIEntityMatch]:
        """Detect all PII entities in text without applying substitutions."""
        cfg = config or PIISanitizerConfig()
        raw_matches: List[Tuple[int, int, PIIEntityType, str, float]] = []

        # 1. Email Addresses
        if cfg.mask_email:
            for m in EMAIL_PATTERN.finditer(text):
                raw_matches.append((m.start(), m.end(), PIIEntityType.EMAIL, m.group(0), 0.99))

        # 2. Social Security Numbers
        if cfg.mask_ssn:
            for m in SSN_PATTERN.finditer(text):
                raw_matches.append((m.start(), m.end(), PIIEntityType.SSN, m.group(0), 0.98))

        # 3. Credit Cards (with Luhn algorithm verification)
        if cfg.mask_credit_card:
            for m in CANDIDATE_CARD_PATTERN.finditer(text):
                matched_str = m.group(0)
                if _luhn_checksum(matched_str):
                    raw_matches.append(
                        (m.start(), m.end(), PIIEntityType.CREDIT_CARD, matched_str, 0.99)
                    )

        # 4. Phone Numbers
        if cfg.mask_phone:
            for m in PHONE_PATTERN.finditer(text):
                matched_str = m.group(0)
                # Verify it has at least 10 digits
                digits_count = sum(c.isdigit() for c in matched_str)
                if 10 <= digits_count <= 15:
                    raw_matches.append(
                        (m.start(), m.end(), PIIEntityType.PHONE_NUMBER, matched_str, 0.95)
                    )

        # 5. API Keys and Secrets
        if cfg.mask_api_key:
            for m in OPENAI_KEY_PATTERN.finditer(text):
                raw_matches.append((m.start(), m.end(), PIIEntityType.API_KEY, m.group(0), 1.0))
            for m in AWS_KEY_PATTERN.finditer(text):
                raw_matches.append((m.start(), m.end(), PIIEntityType.API_KEY, m.group(0), 1.0))
            for m in GITHUB_TOKEN_PATTERN.finditer(text):
                raw_matches.append((m.start(), m.end(), PIIEntityType.API_KEY, m.group(0), 1.0))
            for m in GENERIC_BEARER_PATTERN.finditer(text):
                raw_matches.append((m.start(1), m.end(1), PIIEntityType.API_KEY, m.group(1), 0.92))

        # 6. IP Addresses
        if cfg.mask_ip_address:
            for m in IPV4_PATTERN.finditer(text):
                raw_matches.append((m.start(), m.end(), PIIEntityType.IP_ADDRESS, m.group(0), 0.95))

        # Filter overlapping matches (sort by start ascending, then length descending)
        raw_matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        non_overlapping: List[PIIEntityMatch] = []
        last_end = -1

        counters: Dict[str, int] = {}

        for start, end, entity_type, raw_val, conf in raw_matches:
            if start < last_end:
                continue  # Skip overlapping span

            counters[entity_type.value] = counters.get(entity_type.value, 0) + 1
            idx = counters[entity_type.value]

            # Determine replacement string based on strategy
            if cfg.strategy == MaskingStrategy.TOKEN:
                replacement = f"[{entity_type.value.upper()}_{idx}]"
            elif cfg.strategy == MaskingStrategy.HASH:
                h = hashlib.sha256(raw_val.encode()).hexdigest()[:6]
                replacement = f"[{entity_type.value.upper()}_{h}]"
            else:  # REDACT
                replacement = f"[REDACTED_{entity_type.value.upper()}]"

            non_overlapping.append(
                PIIEntityMatch(
                    entity_type=entity_type,
                    text=raw_val,
                    start=start,
                    end=end,
                    replacement=replacement,
                    confidence=conf,
                )
            )
            last_end = end

        return non_overlapping

    def sanitize(
        self,
        text: str,
        config: Optional[PIISanitizerConfig] = None,
    ) -> PIISanitizationResult:
        """Sanitize text by replacing sensitive PII with tokens or redactions."""
        start_time = time.perf_counter()
        entities = self.detect_entities(text, config)

        token_map: Dict[str, str] = {}
        entities_count: Dict[str, int] = {}

        # Reconstruct sanitized text by substituting intervals from right to left
        sanitized_chars = list(text)
        for entity in sorted(entities, key=lambda e: e.start, reverse=True):
            sanitized_chars[entity.start:entity.end] = list(entity.replacement)
            token_map[entity.replacement] = entity.text
            entities_count[entity.entity_type.value] = (
                entities_count.get(entity.entity_type.value, 0) + 1
            )

        sanitized_text = "".join(sanitized_chars)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if entities:
            logger.info(
                f"[PIISanitizer] Sanitized {len(entities)} PII items ({entities_count}) in {latency_ms:.2f}ms"
            )

        return PIISanitizationResult(
            original_text=text,
            sanitized_text=sanitized_text,
            entities_found=entities,
            entities_count=entities_count,
            token_map=token_map,
            latency_ms=round(latency_ms, 2),
        )

    def restore(
        self,
        sanitized_text: str,
        token_map: Dict[str, str],
    ) -> PIIRestoreResult:
        """Reverse token replacements to restore original sensitive data upon delivery to authorized clients."""
        start_time = time.perf_counter()
        restored_text = sanitized_text
        restored_count = 0

        for token, original in token_map.items():
            if token in restored_text:
                restored_text = restored_text.replace(token, original)
                restored_count += 1

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return PIIRestoreResult(
            restored_text=restored_text,
            tokens_restored_count=restored_count,
            latency_ms=round(latency_ms, 2),
        )

    def evaluate_leakage(
        self,
        context_chunks: List[str],
        generated_text: str,
    ) -> PIILeakageCheckResult:
        """Check whether confidential PII present in retrieved contexts leaked into the model generation unmasked."""
        start_time = time.perf_counter()
        combined_context = " ".join(context_chunks)
        context_entities = self.detect_entities(combined_context)

        if not context_entities:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return PIILeakageCheckResult(
                leaked=False,
                leakage_score=0.0,
                leaked_entities=[],
                total_context_pii_count=0,
                total_leaked_count=0,
                reason="No confidential PII detected in retrieved context passages.",
                latency_ms=round(latency_ms, 2),
            )

        leaked_entities: List[PIIEntityMatch] = []
        for ent in context_entities:
            # If the exact confidential text from context appears in the generated output, it's a leak
            if ent.text in generated_text:
                leaked_entities.append(ent)

        total_context_count = len(context_entities)
        total_leaked_count = len(leaked_entities)
        leakage_score = (
            round(total_leaked_count / total_context_count, 2)
            if total_context_count > 0
            else 0.0
        )
        is_leaked = total_leaked_count > 0
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        reason = (
            f"ALERT: {total_leaked_count} private entities leaked from context into generation"
            if is_leaked
            else f"Safe: All {total_context_count} context PII items remained protected"
        )

        return PIILeakageCheckResult(
            leaked=is_leaked,
            leakage_score=leakage_score,
            leaked_entities=leaked_entities,
            total_context_pii_count=total_context_count,
            total_leaked_count=total_leaked_count,
            reason=reason,
            latency_ms=round(latency_ms, 2),
        )

    def get_presets(self) -> List[PIIPresetScenario]:
        """Return preset evaluation and test scenarios."""
        return PRESET_SCENARIOS


pii_sanitizer = PIISanitizer()
