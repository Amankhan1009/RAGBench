"""Input Rails for pre-execution prompt injection defense, jailbreak blocking, and system prompt protection."""
import re
import time
from typing import List, Tuple

from ragbench.core.logging import logger
from ragbench.guardrails.schemas import GuardrailCheckResult, RailAction, ViolationType

# Regex patterns matching prompt injection and instruction override attempts
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts?|rules?|commands?|guidelines?)",
    r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts?|rules?|commands?)",
    r"forget\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules?)",
    r"override\s+(?:all\s+)?(?:system|safety|security)\s+(?:prompts?|rules?|boundaries?)",
    r"new\s+(?:system\s+)?instructions?\s*:\s*(?:from\s+now\s+on|you\s+are|you\s+must)",
    r"you\s+are\s+no\s+longer\s+(?:an?\s+)?(?:ai|assistant|bound\s+by\s+rules)",
    r"bypass\s+(?:safety|content|all)\s+(?:filters?|restrictions?|policies?)",
    r"clear\s+(?:your\s+)?memory\s+and\s+start\s+fresh\s+as",
]

# Patterns matching popular adversarial jailbreak personas
JAILBREAK_PATTERNS = [
    r"\b(?:dan|aim|stan|kevin)\s+mode\b",
    r"\bdo\s+anything\s+now\b",
    r"\bdeveloper\s+mode\s+(?:enabled|activated|on)\b",
    r"\broleplay\s+as\s+(?:an?\s+)?(?:unfiltered|unrestricted|evil|immoral|jailbroken)\s+(?:ai|assistant|entity)",
    r"\bpretend\s+you\s+have\s+no\s+(?:filters?|rules?|morals?|guidelines?|ethics?)\b",
    r"\bact\s+as\s+(?:an?\s+)?(?:unconstrained|unlimited|unfiltered)\s+(?:model|ai)\b",
    r"\bhypothetical\s+fictional\s+scenario\s+where\s+(?:no\s+rules|safety\s+does\s+not\s+apply)\b",
    r"\bjailbreak(?:ed|ing)?\b",
    r"\balways\s+say\s+yes\s+to\s+every\s+request\b",
]

# Patterns matching system prompt exfiltration attempts
SYSTEM_LEAK_PATTERNS = [
    r"(?:print|output|display|show|reveal|repeat|echo)\s+(?:your\s+)?(?:system\s+prompt|initial\s+instructions?|system\s+message)",
    r"what\s+(?:were|are)\s+the\s+(?:exact\s+)?(?:instructions?|prompts?)\s+(?:given|provided)\s+to\s+you",
    r"output\s+(?:your\s+)?instructions?\s+verbatim",
    r"show\s+me\s+the\s+text\s+before\s+this\s+conversation",
    r"reveal\s+your\s+hidden\s+system\s+(?:prompt|instructions?)",
]


class InputRails:
    """Pre-execution guardrail interceptor running before queries consume model tokens."""

    def __init__(self):
        self.injection_regexes = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]
        self.jailbreak_regexes = [re.compile(p, re.IGNORECASE) for p in JAILBREAK_PATTERNS]
        self.leak_regexes = [re.compile(p, re.IGNORECASE) for p in SYSTEM_LEAK_PATTERNS]

    def check(
        self,
        prompt: str,
        check_jailbreaks: bool = True,
        check_prompt_injection: bool = True,
        check_system_leak: bool = True,
    ) -> GuardrailCheckResult:
        """Inspect prompt for prompt injection, jailbreaks, and system prompt leaks."""
        start_time = time.perf_counter()
        normalized_prompt = " ".join(prompt.strip().split())

        violations: List[str] = []

        # 1. Check Prompt Injection
        if check_prompt_injection:
            for pattern in self.injection_regexes:
                if pattern.search(normalized_prompt):
                    violations.append(ViolationType.PROMPT_INJECTION.value)
                    break

        # 2. Check Jailbreak Attacks
        if check_jailbreaks:
            for pattern in self.jailbreak_regexes:
                if pattern.search(normalized_prompt):
                    violations.append(ViolationType.JAILBREAK.value)
                    break

        # 3. Check System Prompt Exfiltration Attempts
        if check_system_leak:
            for pattern in self.leak_regexes:
                if pattern.search(normalized_prompt):
                    violations.append(ViolationType.SYSTEM_LEAK_ATTEMPT.value)
                    break

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if violations:
            logger.warning(
                f"[InputRails] Intercepted adversarial prompt with violations: {violations} (latency: {latency_ms:.2f}ms)"
            )
            return GuardrailCheckResult(
                passed=False,
                action=RailAction.BLOCK,
                violations=violations,
                confidence=0.98,
                refusal_response=(
                    "I cannot fulfill this request because it violates system security policies regarding "
                    "prompt injection, system prompt confidentiality, or adversarial persona modification."
                ),
                reason=f"Blocked by input rails: {', '.join(violations)}",
                execution_time_ms=round(latency_ms, 2),
            )

        return GuardrailCheckResult(
            passed=True,
            action=RailAction.ALLOW,
            violations=[],
            confidence=1.0,
            reason="Passed all input security guardrails",
            execution_time_ms=round(latency_ms, 2),
        )


# Global singleton instance
input_rails = InputRails()
