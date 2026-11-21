"""Output Rails for post-execution RAG fact-checking and hallucination interception."""
import re
import time
from typing import List, Set

from ragbench.core.logging import logger
from ragbench.guardrails.schemas import GuardrailCheckResult, RailAction, ViolationType

# Common English stopwords to ignore during grounding verification
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "arent", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt",
    "doing", "dont", "down", "during", "each", "few", "for", "from", "further", "had", "hadnt",
    "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here",
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill", "im",
    "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most",
    "mustnt", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shant", "she",
    "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", "that", "thats",
    "the", "their", "theirs", "them", "themselves", "then", "there", "theres", "these", "they",
    "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "werent", "what",
    "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom", "why",
    "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your",
    "yours", "yourself", "yourselves", "also", "can", "will", "just", "like", "one", "two", "three",
}


def _tokenize(text: str) -> Set[str]:
    """Tokenize and extract significant content words (excluding stopwords)."""
    words = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", text.lower())
    return {w for w in words if w not in STOPWORDS}


def _split_into_sentences(text: str) -> List[str]:
    """Segment text into individual sentences for fine-grained claim evaluation."""
    # Split on period, exclamation, or question mark followed by space or newline
    raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 5]
    return sentences or [text.strip()]


class OutputRails:
    """Post-generation fact-checking engine comparing generated claims against retrieved RAG contexts."""

    def check(
        self,
        response_text: str,
        retrieved_contexts: List[str],
        hallucination_threshold: float = 0.5,
    ) -> GuardrailCheckResult:
        """Inspect generated response against retrieved passages to detect hallucinations."""
        start_time = time.perf_counter()

        # If no retrieved contexts are provided, grounding verification cannot run
        if not retrieved_contexts:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return GuardrailCheckResult(
                passed=True,
                action=RailAction.ALLOW,
                violations=[],
                confidence=1.0,
                reason="No retrieved contexts provided; grounding check skipped.",
                execution_time_ms=round(latency_ms, 2),
            )

        # Build unified token corpus from all retrieved passages
        combined_context_text = " ".join(retrieved_contexts)
        context_tokens = _tokenize(combined_context_text)

        if not context_tokens:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return GuardrailCheckResult(
                passed=True,
                action=RailAction.ALLOW,
                violations=[],
                confidence=1.0,
                reason="Retrieved contexts contained no significant tokens.",
                execution_time_ms=round(latency_ms, 2),
            )

        # Break model output into sentences / claims
        sentences = _split_into_sentences(response_text)
        sentence_scores: List[float] = []

        for sentence in sentences:
            sent_tokens = _tokenize(sentence)
            if not sent_tokens:
                continue

            # Fraction of sentence content words present in retrieved contexts
            overlap = sent_tokens.intersection(context_tokens)
            grounding_ratio = len(overlap) / len(sent_tokens)
            sentence_scores.append(grounding_ratio)

        overall_grounding_score = (
            sum(sentence_scores) / len(sentence_scores) if sentence_scores else 1.0
        )
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if overall_grounding_score < hallucination_threshold:
            logger.warning(
                f"[OutputRails] Potential hallucination detected. Grounding score: {overall_grounding_score:.2f} "
                f"< threshold: {hallucination_threshold} ({latency_ms:.2f}ms)"
            )
            disclaimer = (
                f"\n\n⚠️ **[Guardrail Notice]** Grounding score: {overall_grounding_score * 100:.1f}%. "
                "Some statements in this response could not be verified against the provided source documents."
            )
            return GuardrailCheckResult(
                passed=False,
                action=RailAction.FLAG,
                violations=[ViolationType.HALLUCINATION.value, ViolationType.UNGROUNDED_CLAIM.value],
                confidence=round(1.0 - overall_grounding_score, 2),
                sanitized_text=f"{response_text}{disclaimer}",
                reason=(
                    f"Low context grounding ({overall_grounding_score * 100:.1f}% vs threshold "
                    f"{hallucination_threshold * 100:.1f}%)"
                ),
                execution_time_ms=round(latency_ms, 2),
            )

        return GuardrailCheckResult(
            passed=True,
            action=RailAction.ALLOW,
            violations=[],
            confidence=round(overall_grounding_score, 2),
            reason=f"Verified grounded in retrieved contexts ({overall_grounding_score * 100:.1f}%)",
            execution_time_ms=round(latency_ms, 2),
        )


output_rails = OutputRails()
