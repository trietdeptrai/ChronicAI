"""
Response Caching Service for ChronicAI.

Provides in-memory caching for medical AI responses to reduce
LLM load and improve response times for repeated queries.

Features:
- LRU cache with configurable size and TTL
- Query normalization for better cache hits
- Patient-aware caching (different cache per patient context)
- Thread-safe async operations
"""
import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached response entry."""
    response: str
    response_en: Optional[str]
    timestamp: float
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if entry has expired."""
        return time.time() - self.timestamp > ttl_seconds


class ResponseCache:
    """
    LRU cache for medical AI responses.

    Thread-safe, async-compatible cache with TTL support.
    """

    def __init__(
        self,
        max_size: int = 500,
        ttl_seconds: float = 3600.0,  # 1 hour default
        enabled: bool = True
    ):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._enabled = enabled
        self._lock = asyncio.Lock()

        # Statistics
        self._hits = 0
        self._misses = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def _generate_cache_key(
        self,
        query: str,
        patient_ids: Optional[list] = None,
        query_type: Optional[str] = None
    ) -> str:
        """
        Generate a cache key from query and context.

        Normalizes the query for better cache hit rates.
        """
        # Normalize query: lowercase, strip whitespace, remove extra spaces
        normalized_query = " ".join(query.lower().strip().split())

        # Include patient context in key
        patient_key = ""
        if patient_ids:
            patient_key = "_".join(sorted(str(p) for p in patient_ids))

        # Create composite key
        key_parts = [normalized_query]
        if patient_key:
            key_parts.append(f"patients:{patient_key}")
        if query_type:
            key_parts.append(f"type:{query_type}")

        key_string = "|".join(key_parts)

        # Hash for consistent key length
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

    async def get(
        self,
        query: str,
        patient_ids: Optional[list] = None,
        query_type: Optional[str] = None
    ) -> Optional[Tuple[str, Optional[str]]]:
        """
        Get cached response if available.

        Args:
            query: The query string
            patient_ids: Optional list of patient IDs for context
            query_type: Optional query type for more specific caching

        Returns:
            Tuple of (response_vi, response_en) if cached, None otherwise
        """
        if not self._enabled:
            return None

        cache_key = self._generate_cache_key(query, patient_ids, query_type)

        async with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[cache_key]

            # Check expiration
            if entry.is_expired(self._ttl_seconds):
                del self._cache[cache_key]
                self._misses += 1
                logger.debug(f"[Cache] Expired entry for key {cache_key[:8]}...")
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            entry.hit_count += 1
            self._hits += 1

            logger.info(f"[Cache] HIT for query: {query[:50]}... (hits: {entry.hit_count})")
            return (entry.response, entry.response_en)

    async def set(
        self,
        query: str,
        response: str,
        response_en: Optional[str] = None,
        patient_ids: Optional[list] = None,
        query_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Cache a response.

        Args:
            query: The query string
            response: Vietnamese response to cache
            response_en: Optional English response
            patient_ids: Optional list of patient IDs
            query_type: Optional query type
            metadata: Optional metadata to store with entry
        """
        if not self._enabled:
            return

        cache_key = self._generate_cache_key(query, patient_ids, query_type)

        async with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"[Cache] Evicted oldest entry: {oldest_key[:8]}...")

            # Add new entry
            self._cache[cache_key] = CacheEntry(
                response=response,
                response_en=response_en,
                timestamp=time.time(),
                metadata=metadata or {}
            )

            logger.info(f"[Cache] Stored response for query: {query[:50]}...")

    async def invalidate(
        self,
        query: Optional[str] = None,
        patient_ids: Optional[list] = None
    ):
        """
        Invalidate cache entries.

        Args:
            query: Specific query to invalidate
            patient_ids: Invalidate all entries for these patients
        """
        async with self._lock:
            if query:
                # Invalidate specific query
                cache_key = self._generate_cache_key(query, patient_ids)
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.info(f"[Cache] Invalidated query: {query[:50]}...")

            elif patient_ids:
                # Invalidate all entries for patients (more expensive)
                patient_key = "_".join(sorted(str(p) for p in patient_ids))
                keys_to_delete = [
                    k for k, v in self._cache.items()
                    if patient_key in v.metadata.get("patient_key", "")
                ]
                for key in keys_to_delete:
                    del self._cache[key]
                logger.info(f"[Cache] Invalidated {len(keys_to_delete)} entries for patients")

    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"[Cache] Cleared {count} entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "enabled": self._enabled,
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


# Global cache instance
response_cache = ResponseCache(
    max_size=500,
    ttl_seconds=3600.0,  # 1 hour
    enabled=True
)


# Convenience functions
async def get_cached_response(
    query: str,
    patient_ids: Optional[list] = None,
    query_type: Optional[str] = None
) -> Optional[Tuple[str, Optional[str]]]:
    """Get a cached response."""
    return await response_cache.get(query, patient_ids, query_type)


async def cache_response(
    query: str,
    response: str,
    response_en: Optional[str] = None,
    patient_ids: Optional[list] = None,
    query_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Cache a response."""
    await response_cache.set(
        query, response, response_en, patient_ids, query_type, metadata
    )


async def invalidate_patient_cache(patient_ids: list):
    """Invalidate cache for specific patients."""
    await response_cache.invalidate(patient_ids=patient_ids)
