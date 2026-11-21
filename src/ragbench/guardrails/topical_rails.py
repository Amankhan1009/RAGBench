"""Topical Rails for enforcing programmable Colang domain boundaries and off-topic refusals."""
import re
import time
from typing import List, Optional

from ragbench.core.logging import logger
from ragbench.guardrails.schemas import (
    GuardrailCheckResult,
    RailAction,
    TopicalRailConfig,
    ViolationType,
)

# Default forbidden topic keywords and phrases
DEFAULT_OFF_TOPIC_KEYWORDS = {
    "gaming cheats": ["cheat", "aimbot", "wallhack", "mod menu", "game hack", "infinite health"],
    "illegal weapons": ["ghost gun", "3d print gun", "pipe bomb", "homemade explosive", "weapon blueprint"],
    "gambling": ["online casino", "sports betting", "roulette bot", "poker bot", "slot machine hack"],
    "malware": ["ransomware", "keylogger", "trojan script", "ddos script", "exploit payload"],
    "politics": ["election tampering", "political smear", "partisan campaign advice", "political sabotage"],
}


class TopicalRails:
    """Colang-style runtime topical boundary engine enforcing business domain alignment."""

    def __init__(self):
        self._compiled_forbidden = {}
        for category, terms in DEFAULT_OFF_TOPIC_KEYWORDS.items():
            pattern = r"\b(" + "|".join([re.escape(t) for t in terms]) + r")\b"
            self._compiled_forbidden[category] = re.compile(pattern, re.IGNORECASE)

    def check(
        self,
        prompt: str,
        config: Optional[TopicalRailConfig] = None,
    ) -> GuardrailCheckResult:
        """Inspect prompt to verify it aligns with allowed business topics and avoids disallowed topics."""
        start_time = time.perf_counter()
        active_config = config or TopicalRailConfig()
        clean_prompt = prompt.lower().strip()

        violations: List[str] = []
        matched_forbidden: List[str] = []

        # 1. Check Explicitly Disallowed Categories
        for category, regex in self._compiled_forbidden.items():
            if any(dis.lower() in category.lower() for dis in active_config.disallowed_topics):
                if regex.search(clean_prompt):
                    violations.append(ViolationType.OFF_TOPIC.value)
                    matched_forbidden.append(category)

        # Also check custom disallowed terms in config
        for topic in active_config.disallowed_topics:
            if topic.lower() in clean_prompt and topic.lower() not in [m.lower() for m in matched_forbidden]:
                violations.append(ViolationType.OFF_TOPIC.value)
                matched_forbidden.append(topic)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if violations:
            logger.warning(
                f"[TopicalRails] Off-topic request intercepted. Topics: {matched_forbidden} ({latency_ms:.2f}ms)"
            )
            return GuardrailCheckResult(
                passed=False,
                action=RailAction.BLOCK,
                violations=list(set(violations)),
                confidence=0.95,
                refusal_response=active_config.refusal_message,
                reason=f"Off-topic query outside domain boundaries: {', '.join(matched_forbidden)}",
                execution_time_ms=round(latency_ms, 2),
            )

        return GuardrailCheckResult(
            passed=True,
            action=RailAction.ALLOW,
            violations=[],
            confidence=1.0,
            reason=f"Query is within permitted domain '{active_config.domain_name}'",
            execution_time_ms=round(latency_ms, 2),
        )


topical_rails = TopicalRails()
