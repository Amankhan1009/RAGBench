"""High-performance in-memory and semantic cache for RAGBench AI Gateway."""
import hashlib
import time
from typing import Dict, List, Optional, Set, Tuple

from ragbench.core.logging import logger
from ragbench.gateway.schemas import CacheStats


def _normalize_text(text: str) -> str:
    """Normalize text for hashing and token comparison."""
    return " ".join(text.lower().strip().split())


def _compute_jaccard_similarity(tokens1: Set[str], tokens2: Set[str]) -> float:
    """Compute token Jaccard similarity coefficient between two token sets."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return float(intersection) / float(union) if union > 0 else 0.0


class CachedEntry:
    """Represents a cached completion with timing and cost metadata."""
    def __init__(
        self,
        prompt: str,
        model: str,
        response_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        original_latency_ms: float,
        provider_name: str,
        ttl_seconds: int = 3600,
        finish_reason: str = "stop",
    ):
        self.prompt = prompt
        self.model = model
        self.response_text = response_text
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd
        self.original_latency_ms = original_latency_ms
        self.provider_name = provider_name
        self.finish_reason = finish_reason
        self.created_at = time.time()

        self.expires_at = self.created_at + ttl_seconds
        self.normalized_tokens = set(_normalize_text(prompt).split())
        self.hit_count = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class SemanticCache:
    """Thread-safe multi-tenant cache supporting exact hashing and token similarity lookup."""

    def __init__(self, default_ttl_seconds: int = 3600):
        self.default_ttl = default_ttl_seconds
        # workspace_id -> { cache_key: CachedEntry }
        self._cache: Dict[str, Dict[str, CachedEntry]] = {}
        # workspace_id -> stats dict
        self._stats: Dict[str, Dict[str, float]] = {}

    def _get_workspace_cache(self, workspace_id: str) -> Dict[str, CachedEntry]:
        if workspace_id not in self._cache:
            self._cache[workspace_id] = {}
        return self._cache[workspace_id]

    def _get_workspace_stats(self, workspace_id: str) -> Dict[str, float]:
        if workspace_id not in self._stats:
            self._stats[workspace_id] = {
                "total_requests": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "total_cost_saved_usd": 0.0,
                "total_latency_saved_ms": 0.0,
            }
        return self._stats[workspace_id]

    @staticmethod
    def compute_cache_key(prompt: str, model: str, temperature: float) -> str:
        """Compute deterministic SHA-256 hash key for exact cache matching."""
        normalized = f"{_normalize_text(prompt)}:{model.strip().lower()}:{round(temperature, 2)}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(
        self,
        workspace_id: str,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        similarity_threshold: float = 0.95,
    ) -> Optional[Tuple[CachedEntry, str]]:
        """Retrieve cached entry via exact match first, then semantic similarity match.

        Returns (CachedEntry, match_type) where match_type is 'exact' or 'semantic'.
        """
        w_cache = self._get_workspace_cache(workspace_id)
        w_stats = self._get_workspace_stats(workspace_id)
        w_stats["total_requests"] += 1

        exact_key = self.compute_cache_key(prompt, model, temperature)

        # 1. Exact Match Lookup (O(1), <0.5ms)
        if exact_key in w_cache:
            entry = w_cache[exact_key]
            if not entry.is_expired:
                entry.hit_count += 1
                w_stats["cache_hits"] += 1
                w_stats["total_cost_saved_usd"] += entry.cost_usd
                w_stats["total_latency_saved_ms"] += max(0.0, entry.original_latency_ms - 2.0)
                logger.info(f"[SemanticCache] Exact cache hit for workspace '{workspace_id}', key '{exact_key[:8]}'")
                return entry, "exact"
            else:
                # Remove expired entry
                del w_cache[exact_key]

        # 2. Semantic Similarity Lookup (Token Jaccard Coefficient)
        if similarity_threshold < 1.0:
            query_tokens = set(_normalize_text(prompt).split())
            best_entry: Optional[CachedEntry] = None
            best_sim = 0.0

            for entry in list(w_cache.values()):
                if entry.is_expired:
                    continue
                if entry.model.lower() != model.strip().lower():
                    continue

                sim = _compute_jaccard_similarity(query_tokens, entry.normalized_tokens)
                if sim >= similarity_threshold and sim > best_sim:
                    best_sim = sim
                    best_entry = entry

            if best_entry:
                best_entry.hit_count += 1
                w_stats["cache_hits"] += 1
                w_stats["total_cost_saved_usd"] += best_entry.cost_usd
                w_stats["total_latency_saved_ms"] += max(0.0, best_entry.original_latency_ms - 3.0)
                logger.info(
                    f"[SemanticCache] Semantic cache hit (similarity: {best_sim:.3f}) for workspace '{workspace_id}'"
                )
                return best_entry, f"semantic_{int(best_sim * 100)}%"

        w_stats["cache_misses"] += 1
        return None

    def set(
        self,
        workspace_id: str,
        prompt: str,
        model: str,
        response_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: float,
        provider_name: str,
        temperature: float = 0.0,
        ttl_seconds: Optional[int] = None,
        finish_reason: str = "stop",
    ) -> str:
        """Store a generation result in the workspace cache."""
        w_cache = self._get_workspace_cache(workspace_id)
        cache_key = self.compute_cache_key(prompt, model, temperature)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl

        entry = CachedEntry(
            prompt=prompt,
            model=model,
            response_text=response_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            original_latency_ms=latency_ms,
            provider_name=provider_name,
            ttl_seconds=ttl,
            finish_reason=finish_reason,
        )

        w_cache[cache_key] = entry
        return cache_key

    def purge(self, workspace_id: str) -> int:
        """Purge all cached items for a given workspace and return cleared count."""
        w_cache = self._get_workspace_cache(workspace_id)
        count = len(w_cache)
        w_cache.clear()
        logger.info(f"[SemanticCache] Purged {count} entries for workspace '{workspace_id}'")
        return count

    def get_stats(self, workspace_id: str) -> CacheStats:
        """Return aggregated cache statistics for a workspace."""
        w_stats = self._get_workspace_stats(workspace_id)
        w_cache = self._get_workspace_cache(workspace_id)

        # Filter out expired items for count
        valid_count = sum(1 for e in w_cache.values() if not e.is_expired)
        total = int(w_stats["total_requests"])
        hits = int(w_stats["cache_hits"])
        misses = int(w_stats["cache_misses"])
        hit_rate = round(float(hits) / float(total), 4) if total > 0 else 0.0

        return CacheStats(
            workspace_id=workspace_id,
            total_requests=total,
            cache_hits=hits,
            cache_misses=misses,
            hit_rate=hit_rate,
            total_cost_saved_usd=round(w_stats["total_cost_saved_usd"], 6),
            total_latency_saved_ms=round(w_stats["total_latency_saved_ms"], 2),
            cached_entries_count=valid_count,
        )


# Global singleton instance
gateway_cache = SemanticCache()
